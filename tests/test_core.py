from django.test import TestCase
from unittest.mock import MagicMock, patch
from django_semantic_analytics.models import SemanticAtom, FailedQuery
from django_semantic_analytics.services.retriever import AtomRetriever
from django_semantic_analytics.services.assembler import SQLAssembler
from django_semantic_analytics.services.bouncer import SQLBouncer

class TestSemanticPipeline(TestCase):
    def setUp(self):
        # Mock VectorService to avoid API calls during model creation if save() triggers it
        # But here we manually create with embedding, so save logic is bypassed if embedding is present
        self.atom1 = SemanticAtom.objects.create(
            name="Daily Revenue",
            description="Revenue for the day",
            sql_snippet="SUM(revenue)",
            atom_type="METRIC",
            embedding=[0.1]*1536
        )
        self.join_atom = SemanticAtom.objects.create(
            name="Orders Join",
            description="Join orders table",
            sql_snippet="JOIN orders ON ...",
            atom_type="JOIN",
            embedding=[0.2]*1536
        )
        self.atom1.dependencies.add(self.join_atom)

    @patch('django_semantic_analytics.services.retriever.VectorService.get_embedding')
    def test_retriever_dependencies(self, mock_embed):
        mock_embed.return_value = [0.1]*1536
        retriever = AtomRetriever()
        
        # Should return atom1 AND join_atom due to dependency
        atoms = retriever.retrieve_relevant_atoms("Show revenue")
        self.assertIn(self.atom1, atoms)
        self.assertIn(self.join_atom, atoms)

    @patch('django_semantic_analytics.services.assembler.OpenAI')
    def test_assembler_prompt(self, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices[0].message.content = "SELECT SUM(revenue) FROM orders"
        
        assembler = SQLAssembler()
        sql = assembler.assemble_query("dummy", [self.atom1])
        self.assertEqual(sql, "SELECT SUM(revenue) FROM orders")

    def test_bouncer_safety(self):
        bouncer = SQLBouncer()
        
        # Valid
        safe = bouncer.validate_and_format("SELECT * FROM users")
        self.assertIn("LIMIT", safe)
        
        # Invalid
        with self.assertRaises(ValueError):
            bouncer.validate_and_format("DROP TABLE users")
