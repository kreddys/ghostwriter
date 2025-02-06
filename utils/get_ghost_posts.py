import os
import requests
import jwt
import json
from datetime import datetime as date

# Ghost Admin API details
GHOST_ADMIN_API_KEY = os.getenv("GHOST_ADMIN_API_KEY")
GHOST_API_URL = os.getenv("GHOST_APP_URL") + "/ghost/api/admin/posts/?formats=html,lexical&limit=50&page={}"

# Split API key
id, secret = GHOST_ADMIN_API_KEY.split(":")
iat = int(date.now().timestamp())

# Generate JWT token
header = {"alg": "HS256", "typ": "JWT", "kid": id}
payload = {"iat": iat, "exp": iat + 5 * 60, "aud": "/admin/"}
token = jwt.encode(payload, bytes.fromhex(secret), algorithm="HS256", headers=header)

# Create a directory to store posts
folder_name = "ghost_posts"
os.makedirs(folder_name, exist_ok=True)

# Fetch all posts using pagination
page = 1
while True:
    url = GHOST_API_URL.format(page)
    headers = {"Authorization": f"Ghost {token}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        print(f"Error fetching page {page}: {response.status_code}, {response.text}")
        break

    data = response.json()
    posts = data.get("posts", [])
    
    if not posts:
        print("No more posts found.")
        break  # Exit loop when no more posts are available

    # Save each post as a separate JSON file
    for post in posts:
        post_id = post["id"]
        file_path = os.path.join(folder_name, f"{post_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(post, f, indent=4)

    print(f"Saved {len(posts)} posts from page {page}")
    page += 1  # Go to the next page
