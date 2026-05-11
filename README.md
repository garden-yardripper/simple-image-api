A simple image hosting API powered by FastAPI.

In order to host this project yourself, you must create a `.env` file with the required fields, which are displayed in `.env.example`. The `.env` file will automatically be read when the application starts.

The application uses `aiomysql` to manage database connections, and therefore you must have a MySQL or MariaDB database server.