import sqlglot
from sqlglot import exp, parse_one
from django.db import connections
from django.conf import settings

class SQLBouncer:
    def __init__(self, read_replica_alias: str = None):
        # Use a secondary DB if configured, otherwise default to 'default'
        self.db_alias = read_replica_alias or getattr(settings, 'SEMANTIC_ANALYTICS_READ_REPLICA', 'default')
        self.max_limit = getattr(settings, 'SEMANTIC_ANALYTICS_MAX_LIMIT', 1000)

    def validate_and_format(self, sql: str) -> str:
        """
        Perform static analysis and enforce safety rules using sqlglot.
        """
        if sql.startswith("ERROR"):
            raise ValueError(sql)

        try:
            # Parse SQL to ensure it's valid PostgreSQL
            expression = parse_one(sql, read="postgres")
            
            # 1. Safety Check: Only SELECT allowed
            # Ensure no destructive operations exist in the expression tree
            for node, *_ in expression.walk():
                if isinstance(node, (exp.Delete, exp.Update, exp.Drop, exp.Insert, exp.Alter)):
                    raise ValueError(f"Prohibited operation detected: {type(node).__name__}")

            # 2. Limit Enforcement
            # We wrap the original query in a SELECT * FROM (...) LIMIT N to be 100% sure
            # even if the AI tried to ignore the limit.
            final_sql = f"SELECT * FROM ({sql.rstrip(';')}) AS security_wrapper LIMIT {self.max_limit};"
            
            return final_sql
            
        except sqlglot.errors.ParseError as e:
            raise ValueError(f"SQL Syntax Error: {str(e)}")
        except Exception as e:
            raise ValueError(f"Safety Violation: {str(e)}")

    def execute_query(self, sql: str):
        """
        Execute the query on the designated read-only connection and return results as dicts.
        """
        with connections[self.db_alias].cursor() as cursor:
            cursor.execute(sql)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
            return results
