from typing import List, Set
from django.conf import settings
from django.db.models import F
from pgvector.django import CosineDistance
from openai import OpenAI
from ..models import SemanticAtom, VerifiedQuery

class VectorService:
    def __init__(self):
        # Allow passing custom api_key if not in settings for flexibility
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.client = OpenAI(api_key=api_key)
        self.model = getattr(settings, 'SEMANTIC_ANALYTICS_EMBEDDING_MODEL', 'text-embedding-3-small')

    def get_embedding(self, text: str) -> List[float]:
        """Convert text into a vector using OpenAI."""
        response = self.client.embeddings.create(
            input=[text],
            model=self.model
        )
        return response.data[0].embedding

class AtomRetriever:
    def __init__(self, vector_service: VectorService = None):
        self.vector_service = vector_service or VectorService()
        self.top_k = getattr(settings, 'SEMANTIC_ANALYTICS_TOP_K', 10)

    def retrieve_relevant_atoms(self, question: str) -> List[SemanticAtom]:
        """
        Retrieves atoms relevant to the question and resolves their dependencies.
        """
        embedding = self.vector_service.get_embedding(question)
        
        # Pull top-k atoms based on cosine similarity
        initial_atoms = list(
            SemanticAtom.objects.annotate(
                distance=CosineDistance('embedding', embedding)
            ).order_by('distance')[:self.top_k]
        )
        
        # Resolve all dependencies (Joins, etc.) recursively
        resolved_atoms = self._resolve_dependencies(initial_atoms)
        return list(resolved_atoms)

    def find_verified_query(self, question: str, threshold: float = 0.1) -> str:
        """
        Check if a 'Golden Query' exists for a similar question.
        Returns the SQL if found within the distance threshold.
        """
        embedding = self.vector_service.get_embedding(question)
        
        verified = VerifiedQuery.objects.annotate(
            distance=CosineDistance('embedding', embedding)
        ).filter(distance__lte=threshold).order_by('distance').first()
        
        if verified:
            return verified.sql_query
        return None

    def _resolve_dependencies(self, atoms: List[SemanticAtom]) -> Set[SemanticAtom]:
        """
        Recursively find all dependent atoms (like JOINs) for the initial set.
        """
        all_atoms = set(atoms)
        to_process = list(atoms)
        
        while to_process:
            current = to_process.pop()
            # Fetch dependencies using the relationship defined in models.py
            for dep in current.dependencies.all():
                if dep not in all_atoms:
                    all_atoms.add(dep)
                    to_process.append(dep)
                    
        return all_atoms
