from flask import Flask, jsonify, request, abort
from werkzeug.exceptions import BadRequest
from flask_cors import CORS
from utils.utils import Utils

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes

BLOGPOST_STR_COMPONENTS = ["content", "title", "author", "date"]
SORTING_DIRS = ["asc", "desc"]


@app.route('/api/posts')
def get_posts():
    """The "List" endpoint for 'GET' request.method. As per assignment, if
    "sort" and "direction" are in the query string but have illegal values,
    abort(400) (happens from within the Utils method). If there are multiple
    instances of "sort" or "direction" in query string, apply last."""
    blog_posts = Utils.load_storage_data()
    sorting_crit, sorting_in_rev = Utils.validate_sort_query(request.args)
    if sorting_crit:
        try:
            blog_posts = sorted(blog_posts, key=lambda
                                bp: bp[sorting_crit].lower(),
                                reverse=sorting_in_rev)
        except KeyError:  # what is the diff between thoroughness and paranoia
            print("Database has incomplete entries, abort sorting.")
    # if no 'sort' in query string, but yes 'direction', sort by 'id'
    elif sorting_in_rev is not None:
        try:
            blog_posts = sorted(blog_posts, key=lambda bp: bp['id'],
                                reverse=sorting_in_rev)
        except KeyError:
            print("Someone's manually deleted ids from DB alert code yellow.")
    return jsonify(blog_posts), 200


@app.route('/api/posts', methods=['POST'])
def add_post():
    """The "Add" endpoint. Complains about missing required fields, incl. when
    any value is '', as well as about illegal fields present in Body."""
    try:
        post_data = request.get_json()
    except BadRequest:
        abort(400)
    new_bp = {"id": Utils.get_unique_id()}
    for component in BLOGPOST_STR_COMPONENTS:
        value = post_data.get(component, '')
        if not value:
            abort(400)
        new_bp.update({component: value})
    blog_posts = Utils.load_storage_data()
    blog_posts.append(new_bp)
    Utils.write_data_to_storage(blog_posts)
    return new_bp, 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id: int):
    """Rudimentary: if good id, remove the matching dict from storage."""
    if post_id not in Utils.list_extant_ids():
        abort(404)
    blog_posts = Utils.load_storage_data()
    post_to_del = next(bp for bp in blog_posts if bp['id'] == post_id)
    blog_posts.remove(post_to_del)
    Utils.write_data_to_storage(blog_posts)
    message = f"Post with id {post_id} has been deleted successfully."
    return jsonify({"message": message}), 200


@app.route('/api/posts/<int:post_id>', methods=['PUT'])
def update_post(post_id: int):
    """Update blog post. Retains unique id. Retains old values if new ones not
    specified. If bad post_id, early exit. Format updates into dict, remove
    old_bp, then json.dumps() with new dict. Ret json updated_bp & 200"""
    if post_id not in Utils.list_extant_ids():
        abort(404)
    try:
        updates = request.get_json()
        if updates is None:
            raise BadRequest
    except BadRequest:
        abort(400)
    blog_posts = Utils.load_storage_data()
    old_bp = next(bp for bp in blog_posts if bp['id'] == post_id)
    updated_bp = {}
    for k, v in ((k.lower(), v) for k, v in updates.items()):
        if k not in BLOGPOST_STR_COMPONENTS:
            abort(400)
        if not v:
            updated_bp.update({k: old_bp[k]})
        else:
            updated_bp.update({k: v})
    for component in BLOGPOST_STR_COMPONENTS:  # fetch the non-updated too
        if component not in [k.lower() for k in updates.keys()]:
            updated_bp.update({component: old_bp[component]})
    updated_bp.update({"id": post_id})
    blog_posts.remove(old_bp)
    blog_posts.append(updated_bp)
    Utils.write_data_to_storage(blog_posts)
    return jsonify(updated_bp), 200


@app.route('/api/posts/search')
def search_post():
    """Returns a list of blog posts that match at least one of ["title", "id",
    "content"] since not specified by the assignment whether multiple queries
    should be treated as AND or OR."""
    queries = request.args
    blog_posts = Utils.load_storage_data()
    matches = []
    for qr_k, qr_v in queries.items(multi=True):
        if qr_k.lower() == "id":
            try:
                qr_v = int(qr_v)
            except ValueError:
                continue
        for bp in blog_posts:
            for bp_k, bp_v in bp.items():
                # comparing either <int == int> or <str in str>
                if (qr_k.lower() in bp_k.lower() and
                    (Utils.are_both_int(qr_v, bp_v) and qr_v == bp_v) or
                    (Utils.are_neither_int(qr_v, bp_v) and
                     qr_v.lower() in bp_v.lower())):
                    if bp not in matches:
                        matches.append(bp)
    return jsonify(matches), 200


@app.errorhandler(400)
def error_bad_request(error):
    """Handles bad sorting params for 'GET', missing info for 'POST'
    and bad keys for 'PUT'."""
    if request.method == 'GET':
        bad_params = {}
        for k, v in ((k.lower(), v.lower()) for k, v in request.args.items()):
            if k == "sort" and v not in BLOGPOST_STR_COMPONENTS:
                bad_params.update({"for 'sort'": v})
            if k == "direction" and v not in SORTING_DIRS:
                bad_params.update({"for 'direction'": v})
        return jsonify({"Error 400: Illegal sorting params": bad_params}), 400
    else:  # for 'POST' and 'PUT'
        try:
            data = request.get_json()
        except BadRequest as e:
            err_msg = str(e)
            return jsonify({"Error 400: ": err_msg}), 400
        err_dict = {}
        if request.method == 'POST':
            missing_fields = []
            for component in BLOGPOST_STR_COMPONENTS:
                if component not in [k.lower() for k in data.keys()]:
                    missing_fields.append(component)
            if missing_fields:
                err_dict.update({"Error 400: missingFields": missing_fields})
        illegal_fields = []  # for both 'POST' and 'PUT'
        for k, v in data.items():
            if (k.lower() not in BLOGPOST_STR_COMPONENTS and
                    k.lower() != "id"):
                illegal_fields.append(k)
        if illegal_fields:
            err_dict.update({"Error 400: illegal fields": illegal_fields})
        return jsonify(err_dict), 400


@app.errorhandler(404)
def error_not_found(error):
    """Return json informing user the endpoint was not found & 404."""
    err_msg = f"{request.path} Not Found"
    return jsonify({"Error 404: ": err_msg}), 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
