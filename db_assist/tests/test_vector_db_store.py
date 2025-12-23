import pytest
from unittest.mock import patch, MagicMock
from db_assist.db import vector_db_store
from langchain_core.documents import Document

@pytest.fixture
def mock_pgvector():
    with patch('src.db.vector_db_store.PGVector') as mock_pgvector:
        yield mock_pgvector

@pytest.fixture
def mock_psycopg2():
    with patch('src.db.vector_db_store.psycopg2') as mock_psycopg2:
        mock_conn = MagicMock()
        mock_cur = MagicMock()
        mock_psycopg2.connect.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cur
        yield mock_psycopg2, mock_conn, mock_cur

def test_collection_exists(mock_psycopg2):
    _, conn, mock_cur = mock_psycopg2
    mock_cur.fetchone.return_value = [True]
    
    assert vector_db_store.collection_exists(conn, 'my_collection') == True
    
    mock_cur.fetchone.return_value = [False]
    assert vector_db_store.collection_exists(conn, 'my_collection') == False

def test_get_vector_store_exists(mock_psycopg2, mock_pgvector):
    with patch('src.db.vector_db_store.collection_exists', return_value=True):
        store = vector_db_store.get_vector_store()
        mock_pgvector.assert_called_once()
        assert store is not None

def test_get_vector_store_not_exists(mock_psycopg2, mock_pgvector):
    with patch('src.db.vector_db_store.collection_exists', return_value=False):
        store = vector_db_store.get_vector_store()
        mock_pgvector.assert_not_called()
        assert store is None

def test_create_vector_store(mock_pgvector):
    docs = [Document(page_content="test")]
    embeddings = MagicMock()
    
    vector_db_store.create_vector_store(docs, embeddings)
    
    mock_pgvector.from_documents.assert_called_once()

def test_delete_vector_store_exists():
    with patch('src.db.vector_db_store.get_db_connection') as mock_get_conn:
        with patch('src.db.vector_db_store.release_db_connection') as mock_release_conn:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur
            
            with patch('src.db.vector_db_store.collection_exists', return_value=True):
                vector_db_store.delete_vector_store()
                mock_cur.execute.assert_called_once_with(f"DROP TABLE IF EXISTS langchain_pg_collection_{vector_db_store.COLLECTION_NAME};")
                mock_conn.commit.assert_called_once()
                mock_release_conn.assert_called_once_with(mock_conn)

def test_delete_vector_store_not_exists():
    with patch('src.db.vector_db_store.get_db_connection') as mock_get_conn:
        with patch('src.db.vector_db_store.release_db_connection') as mock_release_conn:
            mock_conn = MagicMock()
            mock_cur = MagicMock()
            mock_get_conn.return_value = mock_conn
            mock_conn.cursor.return_value.__enter__.return_value = mock_cur

            with patch('src.db.vector_db_store.collection_exists', return_value=False):
                vector_db_store.delete_vector_store()
                mock_cur.execute.assert_called_once_with(f"DROP TABLE IF EXISTS langchain_pg_collection_{vector_db_store.COLLECTION_NAME};")
                mock_conn.commit.assert_called_once()
                mock_release_conn.assert_called_once_with(mock_conn)

def test_store_in_vector_db_force_recreate(mock_pgvector):
    with patch('src.db.vector_db_store.create_vector_store') as mock_create:
        docs = [Document(page_content="test")]
        embeddings = MagicMock()
        
        vector_db_store.store_in_vector_db(docs, embeddings, force_recreate=True)
        
        mock_create.assert_called_once_with(docs, embeddings)

def test_store_in_vector_db_loads_existing(mock_pgvector):
    with patch('src.db.vector_db_store.get_vector_store') as mock_get:
        mock_get.return_value = "existing_store"
        docs = [Document(page_content="test")]
        embeddings = MagicMock()
        
        store = vector_db_store.store_in_vector_db(docs, embeddings, force_recreate=False)
        
        mock_get.assert_called_once_with(embeddings)
        assert store == "existing_store"

def test_store_in_vector_db_creates_new(mock_pgvector):
    with patch('src.db.vector_db_store.get_vector_store') as mock_get:
        with patch('src.db.vector_db_store.create_vector_store') as mock_create:
            mock_get.return_value = None
            mock_create.return_value = "new_store"
            docs = [Document(page_content="test")]
            embeddings = MagicMock()
            
            store = vector_db_store.store_in_vector_db(docs, embeddings, force_recreate=False)
            
            mock_get.assert_called_once_with(embeddings)
            mock_create.assert_called_once_with(docs, embeddings)
            assert store == "new_store"