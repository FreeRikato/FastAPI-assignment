def test_create_post_success(client, auth_headers):
    response = client.post(
        "/posts",
        json={"title": "Test Post", "content": "Content here"},
        headers=auth_headers
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Test Post"
    assert "id" in data

def test_unauthorized_access(client):
    # Try creating post without token
    response = client.post("/posts", json={"title": "No Auth", "content": "..."})
    assert response.status_code == 401

def test_update_forbidden(client, auth_headers, auth_headers_user2):
    # User 1 creates a post
    create_res = client.post(
        "/posts",
        json={"title": "User1 Post", "content": "Content"},
        headers=auth_headers
    )
    post_id = create_res.json()["id"]

    # User 2 tries to update User 1's post
    update_res = client.put(
        f"/posts/{post_id}",
        json={"title": "Hacked Title"},
        headers=auth_headers_user2
    )
    assert update_res.status_code == 403

def test_get_posts_pagination(client, auth_headers):
    # Create 15 posts
    for i in range(15):
        client.post(
            "/posts",
            json={"title": f"Post {i}", "content": "Content"},
            headers=auth_headers
        )

    # Get first 10
    response = client.get("/posts?skip=0&limit=10")
    data = response.json()
    assert len(data) == 10

    # Get next 5
    response = client.get("/posts?skip=10&limit=10")
    data = response.json()
    assert len(data) == 5

def test_database_rollback_on_constraint_violation(client, auth_headers):
    # 1. Register a user successfully
    client.post("/register", json={"username": "user_A", "email": "shared@email.com", "password": "pwd"})

    # 2. Try to register a DIFFERENT username but SAME EMAIL
    # The API doesn't check email uniqueness in Python, so this hits the DB.
    # The DB raises IntegrityError. FastAPI returns 500 (Internal Server Error) by default.
    response = client.post(
        "/register",
        json={"username": "user_B", "email": "shared@email.com", "password": "pwd"}
    )
    # We expect 500 (DB Error) or 400 (if you added specific handling),
    # but primarily we want to ensure it failed.
    assert response.status_code in [400, 500]

    # 3. Verify Rollback: 'user_B' should NOT exist in the DB
    login_res = client.post("/token", data={"username": "user_B", "password": "pwd"})
    assert login_res.status_code == 401  # Login fails because user_B wasn't saved

    # 4. Verify System Stability: The DB session should still accept valid data
    response_retry = client.post(
        "/register",
        json={"username": "user_C", "email": "unique@email.com", "password": "pwd"}
    )
    assert response_retry.status_code == 200

def test_comment_creation_retrieval(client, auth_headers):
    # Create Post
    post_res = client.post(
        "/posts",
        json={"title": "Discuss", "content": "Topic"},
        headers=auth_headers
    )
    post_id = post_res.json()["id"]

    # Add Comment
    comment_res = client.post(
        f"/posts/{post_id}/comments",
        json={"text": "Nice post!"},
        headers=auth_headers
    )
    assert comment_res.status_code == 200
    assert comment_res.json()["text"] == "Nice post!"

    # Retrieve Comments
    get_res = client.get(f"/posts/{post_id}/comments")
    assert len(get_res.json()) == 1

def test_cascading_delete(client, auth_headers, db_session):
    # Create Post and Comment
    post_res = client.post("/posts", json={"title": "P", "content": "C"}, headers=auth_headers)
    post_id = post_res.json()["id"]

    client.post(f"/posts/{post_id}/comments", json={"text": "Comment"}, headers=auth_headers)

    # Verify comment exists
    assert len(client.get(f"/posts/{post_id}/comments").json()) == 1

    # Delete Post
    client.delete(f"/posts/{post_id}", headers=auth_headers)

    # Verify Post is gone
    assert client.get(f"/posts/{post_id}").status_code == 404

    # Verify Comment is gone (Direct DB check or via API if endpoint existed to get all comments)
    # Using API logic: getting comments for deleted post returns empty or 404 depending on impl.
    # Our impl returns 404 for post first.

    # Let's check DB directly to be sure about Cascade
    from models import Comment
    count = db_session.query(Comment).filter(Comment.post_id == post_id).count()
    assert count == 0

def test_delete_comment_forbidden(client, auth_headers, auth_headers_user2):
    # User 1 creates a post and a comment
    post_res = client.post("/posts", json={"title": "P", "content": "C"}, headers=auth_headers)
    post_id = post_res.json()["id"]

    comment_res = client.post(f"/posts/{post_id}/comments", json={"text": "My Comment"}, headers=auth_headers)
    comment_id = comment_res.json()["id"]

    # User 2 tries to delete User 1's comment
    del_res = client.delete(f"/comments/{comment_id}", headers=auth_headers_user2)
    assert del_res.status_code == 403

    # Verify comment still exists
    get_res = client.get(f"/posts/{post_id}/comments")
    assert len(get_res.json()) == 1

def test_search_posts(client, auth_headers):
    # Create posts: "FastAPI Guide" and "Python Basics"
    client.post("/posts", json={"title": "FastAPI Guide", "content": "A"}, headers=auth_headers)
    client.post("/posts", json={"title": "Python Basics", "content": "B"}, headers=auth_headers)

    # Search for "fastapi" (case-insensitive)
    response = client.get("/posts?search=fastapi")
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "FastAPI Guide"

    # Search for "PYTHON" (case-insensitive)
    response = client.get("/posts?search=PYTHON")
    data = response.json()
    assert len(data) == 1
    assert data[0]["title"] == "Python Basics"

def test_get_post_not_found(client):
    response = client.get("/posts/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Post not found"
