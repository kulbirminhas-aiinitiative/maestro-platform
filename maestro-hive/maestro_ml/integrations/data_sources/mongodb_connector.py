"""
MongoDB Data Source Connector for Maestro ML Platform
"""

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from typing import Optional, List, Dict, Any
import logging
import pandas as pd

logger = logging.getLogger(__name__)


class MongoDBConnector:
    """
    MongoDB connector

    Usage:
        connector = MongoDBConnector(
            host="localhost",
            port=27017,
            database="mydb"
        )

        # Find documents
        results = connector.find("users", {"age": {"$gt": 25}})

        # Insert documents
        connector.insert_many("users", [
            {"name": "Alice", "age": 30},
            {"name": "Bob", "age": 25}
        ])

        # Load to DataFrame
        df = connector.collection_to_dataframe("users")
    """

    def __init__(
        self,
        host: str = "localhost",
        port: int = 27017,
        database: str = "test",
        username: Optional[str] = None,
        password: Optional[str] = None,
        **kwargs
    ):
        """Initialize MongoDB connector"""
        self.database_name = database

        # Build connection string
        if username and password:
            connection_string = f"mongodb://{username}:{password}@{host}:{port}/"
        else:
            connection_string = f"mongodb://{host}:{port}/"

        try:
            self.client = MongoClient(connection_string, **kwargs)
            self.db = self.client[database]

            # Test connection
            self.client.server_info()

            logger.info(f"MongoDB connector initialized: {host}:{port}/{database}")

        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def get_collection(self, collection: str):
        """Get collection object"""
        return self.db[collection]

    def find(
        self,
        collection: str,
        query: Optional[Dict] = None,
        projection: Optional[Dict] = None,
        limit: int = 0,
        sort: Optional[List] = None
    ) -> List[Dict[str, Any]]:
        """
        Find documents in collection

        Args:
            collection: Collection name
            query: Query filter
            projection: Fields to include/exclude
            limit: Maximum documents to return
            sort: Sort specification

        Returns:
            List of documents
        """
        try:
            coll = self.get_collection(collection)
            cursor = coll.find(query or {}, projection)

            if sort:
                cursor = cursor.sort(sort)

            if limit > 0:
                cursor = cursor.limit(limit)

            results = list(cursor)
            logger.debug(f"Found {len(results)} documents in {collection}")
            return results

        except PyMongoError as e:
            logger.error(f"Find failed: {e}")
            raise

    def find_one(
        self,
        collection: str,
        query: Dict,
        projection: Optional[Dict] = None
    ) -> Optional[Dict[str, Any]]:
        """Find single document"""
        try:
            coll = self.get_collection(collection)
            result = coll.find_one(query, projection)

            logger.debug(f"Find one in {collection}: {'found' if result else 'not found'}")
            return result

        except PyMongoError as e:
            logger.error(f"Find one failed: {e}")
            raise

    def insert_one(self, collection: str, document: Dict[str, Any]) -> str:
        """Insert single document"""
        try:
            coll = self.get_collection(collection)
            result = coll.insert_one(document)

            logger.debug(f"Inserted document in {collection}: {result.inserted_id}")
            return str(result.inserted_id)

        except PyMongoError as e:
            logger.error(f"Insert one failed: {e}")
            raise

    def insert_many(self, collection: str, documents: List[Dict[str, Any]]) -> List[str]:
        """Insert multiple documents"""
        try:
            coll = self.get_collection(collection)
            result = coll.insert_many(documents)

            inserted_ids = [str(id) for id in result.inserted_ids]
            logger.info(f"Inserted {len(inserted_ids)} documents in {collection}")
            return inserted_ids

        except PyMongoError as e:
            logger.error(f"Insert many failed: {e}")
            raise

    def update_one(
        self,
        collection: str,
        query: Dict,
        update: Dict,
        upsert: bool = False
    ) -> int:
        """Update single document"""
        try:
            coll = self.get_collection(collection)
            result = coll.update_one(query, update, upsert=upsert)

            logger.debug(
                f"Update one in {collection}: "
                f"{result.matched_count} matched, {result.modified_count} modified"
            )
            return result.modified_count

        except PyMongoError as e:
            logger.error(f"Update one failed: {e}")
            raise

    def update_many(
        self,
        collection: str,
        query: Dict,
        update: Dict,
        upsert: bool = False
    ) -> int:
        """Update multiple documents"""
        try:
            coll = self.get_collection(collection)
            result = coll.update_many(query, update, upsert=upsert)

            logger.info(
                f"Update many in {collection}: "
                f"{result.matched_count} matched, {result.modified_count} modified"
            )
            return result.modified_count

        except PyMongoError as e:
            logger.error(f"Update many failed: {e}")
            raise

    def delete_one(self, collection: str, query: Dict) -> int:
        """Delete single document"""
        try:
            coll = self.get_collection(collection)
            result = coll.delete_one(query)

            logger.debug(f"Delete one in {collection}: {result.deleted_count} deleted")
            return result.deleted_count

        except PyMongoError as e:
            logger.error(f"Delete one failed: {e}")
            raise

    def delete_many(self, collection: str, query: Dict) -> int:
        """Delete multiple documents"""
        try:
            coll = self.get_collection(collection)
            result = coll.delete_many(query)

            logger.info(f"Delete many in {collection}: {result.deleted_count} deleted")
            return result.deleted_count

        except PyMongoError as e:
            logger.error(f"Delete many failed: {e}")
            raise

    def aggregate(self, collection: str, pipeline: List[Dict]) -> List[Dict]:
        """Run aggregation pipeline"""
        try:
            coll = self.get_collection(collection)
            results = list(coll.aggregate(pipeline))

            logger.debug(f"Aggregation in {collection} returned {len(results)} results")
            return results

        except PyMongoError as e:
            logger.error(f"Aggregation failed: {e}")
            raise

    def collection_to_dataframe(
        self,
        collection: str,
        query: Optional[Dict] = None,
        projection: Optional[Dict] = None
    ) -> pd.DataFrame:
        """Load collection to DataFrame"""
        try:
            documents = self.find(collection, query, projection)

            # Remove _id if present
            for doc in documents:
                if '_id' in doc:
                    doc['_id'] = str(doc['_id'])

            df = pd.DataFrame(documents)
            logger.info(f"Loaded {len(df)} documents to DataFrame from {collection}")
            return df

        except Exception as e:
            logger.error(f"Collection to DataFrame failed: {e}")
            raise

    def dataframe_to_collection(
        self,
        df: pd.DataFrame,
        collection: str,
        if_exists: str = "append"
    ):
        """Write DataFrame to collection"""
        try:
            if if_exists == "replace":
                coll = self.get_collection(collection)
                coll.delete_many({})

            documents = df.to_dict("records")
            self.insert_many(collection, documents)

            logger.info(f"Wrote {len(documents)} documents to {collection}")

        except Exception as e:
            logger.error(f"DataFrame to collection failed: {e}")
            raise

    def close(self):
        """Close MongoDB connection"""
        if hasattr(self, 'client'):
            self.client.close()
            logger.info("MongoDB connection closed")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
