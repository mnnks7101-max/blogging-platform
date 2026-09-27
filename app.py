from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)

app.config["SECRET_KEY"] = "my-secret-key"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///blog.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db = SQLAlchemy(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# User table
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


# Home page
@app.route("/")
def index():
    posts = Post.query.order_by(Post.id.desc()).all()
    comments = Comment.query.order_by(Comment.id.asc()).all()

    return render_template(
        "index.html",
        posts=posts,
        comments=comments
    )

# Register
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        existing_user = User.query.filter_by(username=username).first()

        if existing_user:
            flash("Username already exists!")
            return redirect(url_for("register"))

        hashed_password = generate_password_hash(password)

        new_user = User(
            username=username,
            password=hashed_password
        )

        db.session.add(new_user)
        db.session.commit()

        flash("Registration successful! Please login.")
        return redirect(url_for("login"))

    return render_template("register.html")


# Login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()

        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("index"))

        flash("Invalid username or password!")

    return render_template("login.html")


# Logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

# REST API - Get all posts
@app.route("/api/posts", methods=["GET"])
def api_get_posts():
    posts = Post.query.order_by(Post.id.desc()).all()

    return {
        "posts": [
            {
                "id": post.id,
                "title": post.title,
                "content": post.content,
                "user_id": post.user_id
            }
            for post in posts
        ]
    }


# REST API - Get one post
@app.route("/api/posts/<int:post_id>", methods=["GET"])
def api_get_post(post_id):
    post = Post.query.get_or_404(post_id)

    return {
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "user_id": post.user_id
    }
    # REST API - Create post
@app.route("/api/posts", methods=["POST"])
def api_create_post():
    data = request.get_json()

    title = data.get("title")
    content = data.get("content")
    user_id = data.get("user_id")

    if not title or not content or not user_id:
        return {"error": "title, content and user_id are required"}, 400

    post = Post(
        title=title,
        content=content,
        user_id=user_id
    )

    db.session.add(post)
    db.session.commit()

    return {
        "message": "Post created successfully",
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "user_id": post.user_id
    }, 201


# REST API - Update post
@app.route("/api/posts/<int:post_id>", methods=["PUT"])
def api_update_post(post_id):
    post = Post.query.get_or_404(post_id)

    data = request.get_json()

    post.title = data.get("title", post.title)
    post.content = data.get("content", post.content)

    db.session.commit()

    return {
        "message": "Post updated successfully",
        "id": post.id,
        "title": post.title,
        "content": post.content,
        "user_id": post.user_id
    }


# REST API - Delete post
@app.route("/api/posts/<int:post_id>", methods=["DELETE"])
def api_delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    db.session.delete(post)
    db.session.commit()

    return {
        "message": "Post deleted successfully"
    }
# Create database

# Blog Post table
class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)

class Comment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    post_id = db.Column(db.Integer, db.ForeignKey("post.id"), nullable=False)

# Create post
@app.route("/create_post", methods=["GET", "POST"])
@login_required
def create_post():
    if request.method == "POST":
        title = request.form["title"]
        content = request.form["content"]

        post = Post(
            title=title,
            content=content,
            user_id=current_user.id
        )

        db.session.add(post)
        db.session.commit()

        return redirect(url_for("index"))

    return render_template("create_post.html")
# Create database tables
# Edit post
@app.route("/edit_post/<int:post_id>", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        return "You are not allowed to edit this post."

    if request.method == "POST":
        post.title = request.form["title"]
        post.content = request.form["content"]

        db.session.commit()

        return redirect(url_for("index"))

    return render_template("edit_post.html", post=post)


# Delete post
@app.route("/delete_post/<int:post_id>")
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)

    if post.user_id != current_user.id:
        return "You are not allowed to delete this post."

    db.session.delete(post)
    db.session.commit()

    return redirect(url_for("index"))

    # Add comment
@app.route("/comment/<int:post_id>", methods=["POST"])
@login_required
def add_comment(post_id):
    content = request.form["content"]

    comment = Comment(
        content=content,
        user_id=current_user.id,
        post_id=post_id
    )

    db.session.add(comment)
    db.session.commit()

    return redirect(url_for("index"))
with app.app_context():
    db.create_all()


if __name__ == "__main__":
    app.run(debug=True)
