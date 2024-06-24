import sys
from flask import Flask, jsonify, request, abort
from flask_cors import CORS
from utils.utils import Utils

app = Flask(__name__)
CORS(app)  # This will enable CORS for all routes


@app.route('/api/posts', methods=['GET', 'POST'])
def get_posts():
    if request.method == 'GET':
        return jsonify(Utils.load_storage_data())
    data = request.get_json()
    new_post_title = data.get("title", '')
    new_post_content = data.get("content", '')
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
    blog_posts = Utils.load_storage_data()
    message = ''
    for bp in blog_posts:
        if bp.get('id') == post_id:
            blog_posts.remove(bp)
            Utils.write_data_to_storage(blog_posts)
            message = f"Post with id {post_id} has been deleted successfully."
            break
    if not message:
        abort(404)
    return jsonify({"message": message}), 200


@app.route('/update/<int:post_id>', methods=['GET', 'POST'])
def update(post_id: int):
    """Update blog post (delete old, save data to storage with new). Retains
    unique id. If bad post_id, early exit back to index. If 'GET', display
    update.html; else (means method == 'POST') format POSTed data into dict,
    remove the previously stored dict, then dump with new dict to json."""
    if post_id not in Utils.list_extant_ids():
        return redirect(url_for('index'))
    blog_posts = Utils.load_storage_data()
    post_to_upd = next(bp for bp in blog_posts if bp['id'] == post_id)
    if request.method == 'GET':
        return render_template('update.html').format(
            post_id,
            post_to_upd.get('title', '<untitled>'),
            post_to_upd.get('author', '<unknown>'),
            post_to_upd.get('content', '<unpopulated>')
        )
    new_post_title = request.form.get('title', '<blank>')
    new_post_author = request.form.get('author', '<blank>')
    new_post_content = request.form.get('content', '')
    blog_posts.append(
        {"id": post_id, "author": new_post_author,
         "likes": post_to_upd.get("likes", 0),
         "title": new_post_title, "content": new_post_content}
    )
    blog_posts.remove(post_to_upd)
    Utils.write_data_to_storage(blog_posts)
    return redirect(url_for('index'))


@app.errorhandler(400)
def error_bad_request(error):
    """Return json indicating which key was missing from the body & 400."""
    data = request.get_json()
    missing_fields = []
    if not data.get("content"):
        missing_fields.append("content")
    if not data.get("title"):
        missing_fields.append("title")
    return jsonify({"missingFields": missing_fields}), 400


@app.errorhandler(404)
def error_not_found(error):
    """Return json informing user the endpoint was not found & 404."""
    err_msg = f"404: {request.url} Not Found"
    return jsonify({"Error": err_msg}), 404


if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5002, debug=True)
