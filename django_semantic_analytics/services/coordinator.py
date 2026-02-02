from .retriever import AtomRetriever
from .assembler import SQLAssembler
from .bouncer import SQLBouncer
from ..models import FailedQuery

class SemanticAnalyticsService:
    """
    Main entry point for the semantic analytics package. 
    Coordinatest retrieval, assembly, safety checks, and execution.
    """
    def __init__(self, read_replica: str = None):
        self.retriever = AtomRetriever()
        self.assembler = SQLAssembler()
        self.bouncer = SQLBouncer(read_replica_alias=read_replica)

    def ask(self, question: str):
        """
        Processes a natural language question and returns data results.
        """
        # 1. Check for a manually approved 'Golden Query' first (Cache/Verified layer)
        verified_sql = self.retriever.find_verified_query(question)
        if verified_sql:
            # Verified queries still go through the bouncer for LIMIT & execution routing
            safe_sql = self.bouncer.validate_and_format(verified_sql)
            return self.bouncer.execute_query(safe_sql)

        # 2. Retrieve Trusted Semantic Atoms (The RAG layer)
        atoms = self.retriever.retrieve_relevant_atoms(question)
        
        # 3. Assemble SQL using LLM (The Assembly layer)
        sql = self.assembler.assemble_query(question, atoms)
        
        # 4. Validate, Format, and Execute (The Safety & Execution layer)
        try:
            safe_sql = self.bouncer.validate_and_format(sql)
            results = self.bouncer.execute_query(safe_sql)
            return results
        except Exception as e:
            # 5. Log the failure for human review (The Fix workflow)
            FailedQuery.objects.create(
                question=question,
                attempted_sql=sql if not sql.startswith("ERROR") else None,
                error_message=str(e)
            )
            # Re-raise so the UI can show a graceful error
            raise e
