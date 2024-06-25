from flask import Flask, jsonify, request, abort
from werkzeug.exceptions import BadRequest
from flask_cors import CORS
from utils.utils import Utils

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes


@app.route('/api/posts')
def get_posts():
    """The "List" endpoint for 'GET' request.method. As per assignment, if
    "sort" and "direction" are in the query string but have illegal values,
    abort(400) (happens from within the Utils method). If there are multiple
    instances of "sort" or "direction" in query string, apply last."""
    blog_posts = Utils.load_storage_data()
    sorting_crit, sorting_in_rev = Utils.validate_sort_query(request.args)
    if sorting_crit:
        blog_posts = sorted(blog_posts, key=lambda
                            bp: bp[sorting_crit].lower(),
                            reverse=sorting_in_rev)
    # if no 'sort' in query string, but yes 'direction', sort by 'id'
    elif sorting_in_rev is not None:
        blog_posts = sorted(blog_posts, key=lambda bp: bp['id'],
                            reverse=sorting_in_rev)
    return jsonify(blog_posts), 200


@app.route('/api/posts', methods=['POST'])
def add_post():
    """The "Add" endpoint."""
    try:
        post_data = request.get_json()
    except BadRequest:
        abort(400)
    new_post_title = post_data.get("title", '')
    new_post_content = post_data.get("content", '')
    if not new_post_title or not new_post_content:
        abort(400)
    new_post_id = Utils.get_unique_id()
    new_bp = {"id": new_post_id,
              "title": new_post_title, "content": new_post_content}
    blog_posts = Utils.load_storage_data()
    blog_posts.append(new_bp)
    Utils.write_data_to_storage(blog_posts)
    return new_bp, 201


@app.route('/api/posts/<int:post_id>', methods=['DELETE'])
def delete_post(post_id: int):
    """Rudimentary: if good id, remove the matching dict from storage. No
    indication of failure, just goes back to index either way."""
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
    old_bp dict, then json.dumps() with new dict. Ret json updated_bp & 200"""
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
    if "title" not in updates or "content" not in updates:
        abort(400)
    updated_bp = {}
    for k, v in updates.items():
        if not v:
            updated_bp.update({k: old_bp[k]})
        else:
            updated_bp.update({k: v})
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
    """If request method was 'GET', then query string was off, return json
    informing listing the bad sorting parameters. Else, method was 'PUT',
    return json indicating which key was missing from the body & 400."""
    if request.method == 'GET':
        bad_params = {}
        for k, v in request.args.items():
            if k.lower() == "sort" and (v.lower() != "title" and
                                        v.lower() != "content"):
                bad_params.update({"for 'sort'": v.lower()})
            if k.lower() == "direction" and (v.lower() != "asc" and
                                             v.lower() != "desc"):
                bad_params.update({"for 'direction'": v.lower()})
        return jsonify({"Error 400: Illegal sorting parameters": bad_params}), 400
    try:
        data = request.get_json()
    except BadRequest as e:
        err_msg = str(e)
        return jsonify({"Error": err_msg}), 400
    missing_fields = []
    if not data.get("content"):
        missing_fields.append("content")
    if not data.get("title"):
        missing_fields.append("title")
    return jsonify({"Error 400: missingFields": missing_fields}), 400


@app.errorhandler(404)
def error_not_found(error):
    """Return json informing user the endpoint was not found & 404."""
    err_msg = f"{request.path} Not Found"
    return jsonify({"Error 404: ": err_msg}), 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
