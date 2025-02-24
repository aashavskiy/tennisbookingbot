# File: db.py
# Database connection and operations for the Tennis Booking Bot

import os
import sqlalchemy
from sqlalchemy import create_engine, text
import pymysql
from config import (
    DB_USER, 
    DB_PASS, 
    DB_NAME, 
    DB_HOST, 
    INSTANCE_CONNECTION_NAME, 
    IS_CLOUD_RUN,
    ADMIN_ID,
    logger
)

# Global database connection pool
db = None

def create_database_engine():
    """Creates a database engine connection without specifying a database."""
    try:
        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
        
        if IS_CLOUD_RUN:
            # For Cloud Run, use Unix socket without database name
            socket_path = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
            connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASS}@/"
            
            # Add Unix socket parameter
            params = {
                "unix_socket": socket_path
            }
            
            engine = sqlalchemy.create_engine(
                connection_string,
                connect_args=params,
                **db_config
            )
        else:
            # For local development, use TCP without database name
            host_args = DB_HOST.split(":")
            host = host_args[0]
            port = int(host_args[1]) if len(host_args) > 1 else 3306
            
            engine = sqlalchemy.create_engine(
                sqlalchemy.engine.url.URL.create(
                    drivername="mysql+pymysql",
                    username=DB_USER,
                    password=DB_PASS,
                    host=host,
                    port=port,
                ),
                **db_config
            )
        
        return engine
    except Exception as e:
        logger.error(f"error creating database engine: {str(e)}")
        raise e

def init_connection_engine():
    """Initializes a connection pool for a Cloud SQL MySQL database."""
    try:
        # When deployed to Cloud Run, we can use the Unix socket
        if IS_CLOUD_RUN:
            logger.info("using unix socket connection for cloud run")
            return init_unix_connection_engine()
        # When running locally, use a TCP socket
        else:
            logger.info("using tcp connection for local development")
            return init_tcp_connection_engine()
    except Exception as e:
        # Check if the error is about missing database
        if "Unknown database" in str(e):
            logger.info("database does not exist, attempting to create it")
            try:
                # Create a connection without specifying a database
                create_db_engine = create_database_engine()
                with create_db_engine.connect() as conn:
                    conn.execute(text(f"CREATE DATABASE IF NOT EXISTS {DB_NAME}"))
                    logger.info(f"successfully created database: {DB_NAME}")
                
                # Now try to reconnect with the database specified
                if IS_CLOUD_RUN:
                    return init_unix_connection_engine()
                else:
                    return init_tcp_connection_engine()
            except Exception as create_error:
                logger.error(f"failed to create database: {str(create_error)}")
                raise create_error
        else:
            logger.error(f"error initializing connection engine: {str(e)}")
            raise e

def init_tcp_connection_engine():
    """Initialize a TCP connection pool for a Cloud SQL instance."""
    try:
        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
        
        # MySQL connection URL
        host_args = DB_HOST.split(":")
        host = host_args[0]
        port = int(host_args[1]) if len(host_args) > 1 else 3306
        
        logger.info(f"attempting to connect to mysql at: {host}:{port}")
        
        pool = sqlalchemy.create_engine(
            sqlalchemy.engine.url.URL.create(
                drivername="mysql+pymysql",
                username=DB_USER,
                password=DB_PASS,
                host=host,
                port=port,
                database=DB_NAME,
            ),
            **db_config
        )
        
        # Test the connection
        with pool.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("database connection test successful")
        
        logger.info("created tcp connection pool")
        return pool
    except Exception as e:
        logger.error(f"error creating tcp connection: {str(e)}")
        raise e

def init_unix_connection_engine():
    """Initialize a Unix socket connection pool for a Cloud SQL instance."""
    try:
        db_config = {
            "pool_size": 5,
            "max_overflow": 2,
            "pool_timeout": 30,
            "pool_recycle": 1800,
        }
        
        # The Unix socket path for Cloud Run
        socket_path = f"/cloudsql/{INSTANCE_CONNECTION_NAME}"
        
        # Log the socket path for debugging
        logger.info(f"attempting to connect using unix socket at: {socket_path}")
        
        # Connection string for MySQL
        connection_string = f"mysql+pymysql://{DB_USER}:{DB_PASS}@/{DB_NAME}?unix_socket={socket_path}"
        logger.info(f"connection string (redacted password): {connection_string.replace(DB_PASS, '******')}")
        
        pool = sqlalchemy.create_engine(
            connection_string,
            **db_config
        )
        
        # Test the connection
        with pool.connect() as conn:
            conn.execute(text("SELECT 1"))
            logger.info("database connection test successful")
        
        logger.info("created unix connection pool")
        return pool
    except Exception as e:
        logger.error(f"error creating unix socket connection: {str(e)}")
        # Provide more detailed error information
        if "FileNotFoundError" in str(e):
            logger.error(f"unix socket file not found. verify that cloud sql connection is configured properly.")
            logger.error(f"ensure the cloud run service has the cloud sql instance added as a connection.")
        raise e

def init_db():
    """Initializes the database tables"""
    global db
    
    if db is None:
        logger.error("cannot initialize database - connection pool is not available")
        return False
        
    try:
        # Create tables if they don't exist
        with db.connect() as conn:
            # Create bookings table
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS bookings (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(32) NOT NULL,
                    date VARCHAR(32),
                    time VARCHAR(32),
                    court VARCHAR(32),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            '''))
            
            # Create users table
            conn.execute(text('''
                CREATE TABLE IF NOT EXISTS users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    user_id VARCHAR(32) UNIQUE NOT NULL,
                    username VARCHAR(255),
                    is_admin TINYINT DEFAULT 0,
                    is_approved TINYINT DEFAULT 0
                );
            '''))
            
            # Check if admin user exists
            result = conn.execute(text(
                "SELECT COUNT(*) FROM users WHERE user_id = :admin_id"
            ), {"admin_id": ADMIN_ID})
            
            count = result.fetchone()[0]
            
            # Add admin user if not exists
            if count == 0:
                conn.execute(text('''
                    INSERT INTO users (user_id, username, is_admin, is_approved)
                    VALUES (:admin_id, 'Admin', 1, 1)
                '''), {"admin_id": ADMIN_ID})
                logger.info(f"added admin user with id {ADMIN_ID}")
            
        logger.info("database initialized successfully")
        return True
    except Exception as e:
        logger.error(f"error initializing database: {str(e)}")
        return False

def get_users():
    """Retrieves all users"""
    if db is None:
        logger.error("database connection not available")
        return []
        
    try:
        with db.connect() as conn:
            result = conn.execute(text(
                "SELECT user_id, username, is_admin, is_approved FROM users"
            ))
            return result.fetchall()
    except Exception as e:
        logger.error(f"error getting users: {str(e)}")
        return []

def is_user_admin(user_id):
    """Checks if the user is an admin"""
    if db is None:
        logger.error("database connection not available")
        return False
        
    try:
        with db.connect() as conn:
            result = conn.execute(text(
                "SELECT is_admin FROM users WHERE user_id = :user_id"
            ), {"user_id": user_id})
            row = result.fetchone()
            return row is not None and row[0] == 1
    except Exception as e:
        logger.error(f"error checking admin status: {str(e)}")
        return False

def is_user_approved(user_id):
    """Checks if the user is approved"""
    if db is None:
        logger.error("database connection not available")
        return False
        
    try:
        with db.connect() as conn:
            result = conn.execute(text(
                "SELECT is_approved FROM users WHERE user_id = :user_id"
            ), {"user_id": user_id})
            row = result.fetchone()
            return row is not None and row[0] == 1
    except Exception as e:
        logger.error(f"error checking approval status: {str(e)}")
        return False

def approve_user(user_id):
    """Approves a user"""
    if db is None:
        logger.error("database connection not available")
        return False
        
    try:
        with db.connect() as conn:
            conn.execute(text(
                "UPDATE users SET is_approved = 1 WHERE user_id = :user_id"
            ), {"user_id": user_id})
            logger.info(f"user {user_id} approved successfully")
            return True
    except Exception as e:
        logger.error(f"error approving user: {str(e)}")
        return False

def save_booking(user_id, date, time, court):
    """Saves booking information to database"""
    if db is None:
        logger.error("database connection not available")
        return False
        
    try:
        with db.connect() as conn:
            conn.execute(text('''
                INSERT INTO bookings (user_id, date, time, court)
                VALUES (:user_id, :date, :time, :court)
            '''), {
                "user_id": user_id,
                "date": date,
                "time": time,
                "court": court
            })
            logger.info(f"booking saved for user {user_id} on {date} at {time}, court {court}")
            return True
    except Exception as e:
        logger.error(f"error saving booking: {str(e)}")
        return False

def get_user_bookings(user_id):
    """Retrieves all bookings for a specific user"""
    if db is None:
        logger.error("database connection not available")
        return []
        
    try:
        with db.connect() as conn:
            result = conn.execute(text('''
                SELECT date, time, court, created_at 
                FROM bookings 
                WHERE user_id = :user_id 
                ORDER BY date, time
            '''), {"user_id": user_id})
            return result.fetchall()
    except Exception as e:
        logger.error(f"error retrieving bookings: {str(e)}")
        return []

def create_user(user_id, username, is_admin=0, is_approved=0):
    """Creates a new user in the database"""
    if db is None:
        logger.error("database connection not available")
        return False
        
    try:
        with db.connect() as conn:
            conn.execute(text('''
                INSERT INTO users (user_id, username, is_admin, is_approved) 
                VALUES (:user_id, :username, :is_admin, :is_approved)
                ON DUPLICATE KEY UPDATE username = :username
            '''), {
                "user_id": user_id, 
                "username": username or "Unknown", 
                "is_admin": is_admin, 
                "is_approved": is_approved
            })
            logger.info(f"created or updated user {user_id}")
            return True
    except Exception as e:
        logger.error(f"error creating user: {str(e)}")
        return False

def check_user_status(user_id):
    """Checks if user exists and returns approval status"""
    if db is None:
        logger.error("database connection not available")
        return None
        
    try:
        with db.connect() as conn:
            result = conn.execute(text(
                "SELECT is_approved FROM users WHERE user_id = :user_id"
            ), {"user_id": user_id})
            row = result.fetchone()
            return row[0] if row else None
    except Exception as e:
        logger.error(f"error checking user status: {str(e)}")
        return None

# Initialize the database connection
def initialize_db():
    global db
    try:
        db = init_connection_engine()
        logger.info("database connection pool initialized")
        return db
    except Exception as e:
        logger.error(f"failed to initialize database connection: {str(e)}")
        db = None
        return None