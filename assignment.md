### Assignment 1: User Registration System with Database
**Create a user management system with PostgreSQL/SQLite**

**Requirements:**
*   Set up SQLAlchemy with async engine and create User table
*   User model: id, email, username, hashed_password, created_at, is_active
*   Implement POST /register - Create new user (hash password with bcrypt)
*   Implement POST /login - Authenticate user and return JWT token
*   Implement GET /users/me - Get current user profile (protected route)
*   Implement PUT /users/me - Update user profile (protected route)
*   Email must be unique and validate email format
*   Password must be minimum 8 characters with at least one number
*   Use Pydantic models to exclude password from responses
*   Store tokens securely and validate them on protected routes

**Expected Outcomes:**
*   Master async database operations with SQLAlchemy
*   Implement secure password hashing with bcrypt
*   Create JWT-based authentication system
*   Use dependency injection for route protection

***

### Assignment 2: Weather Data API with External API Integration and Caching
**Build API that fetches, caches, and serves weather data**

**Requirements:**
*   Integrate with OpenWeatherMap or WeatherAPI (free tier available)
*   Implement GET /weather/{city} - Fetch current weather for city
*   Implement GET /weather/forecast/{city} - Get 5-day forecast
*   Cache responses using in-memory dictionary (10-minute expiration)
*   Implement GET /weather/cache-status - Return cache statistics
*   Handle external API errors gracefully (return 503 if weather service unavailable)
*   Add rate limiting: maximum 10 requests per minute per IP address
*   Use httpx AsyncClient for non-blocking external API calls
*   Return standardized response format even when external API format changes
*   Implement request timeout (5 seconds) for external API calls
*   Add logging for API calls, cache hits/misses, and errors
*   Invalidate cache manually via DELETE /weather/cache

**Expected Outcomes:**
*   Integrate external APIs using async httpx
*   Implement caching strategy
*   Master rate limiting and request throttling
*   Handle timeouts and network errors gracefully
*   Understand standardization patterns for external data

***

### Assignment 3: Blog API with Comprehensive Testing Suite
**Develop a blog platform with full CRUD, relationships, and test coverage**

**Requirements:**

**Models:**
*   User: id, username, email, hashed_password, created_at
*   Post: id, title, content, author_id, created_at, updated_at
*   Comment: id, text, post_id, author_id, created_at

**Implement complete CRUD for posts:**
*   POST /posts - Create post (only authenticated users)
*   GET /posts - List posts with pagination and search
*   GET /posts/{post_id} - Get single post with comments
*   PUT /posts/{post_id} - Update post (only author can update)
*   DELETE /posts/{post_id} - Delete post (only author can delete)

**Implement comments:**
*   POST /posts/{post_id}/comments - Add comment (only authenticated)
*   GET /posts/{post_id}/comments - Get all comments for post
*   DELETE /comments/{comment_id} - Delete comment (only author)

**Write pytest test cases covering:**
*   Successful post creation with valid token
*   401 Unauthorized error when accessing protected route without token
*   403 Forbidden error when updating another user's post
*   Post retrieval with pagination
*   Database rollback on validation errors
*   Comment creation and retrieval
*   Cascading delete (post deletion removes associated comments)
*   Achieve minimum 80% code coverage

**Testing Implementation:**
*   Use TestClient for endpoint testing with test Database
*   Mock database to isolate unit tests
*   Include both positive and negative test cases

**Expected Outcomes:**
*   Master database relationships (one-to-many, many-to-many)
*   Implement authorization checks at route level
*   Write comprehensive test suites with pytest
*   Achieve code coverage targets
*   Practice test-driven development (TDD)
