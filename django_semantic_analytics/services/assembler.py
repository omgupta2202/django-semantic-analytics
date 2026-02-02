import json
from typing import List
from django.conf import settings
from openai import OpenAI
from ..models import SemanticAtom

class SQLAssembler:
    def __init__(self, model: str = None):
        api_key = getattr(settings, 'OPENAI_API_KEY', None)
        self.client = OpenAI(api_key=api_key)
        self.model = model or getattr(settings, 'SEMANTIC_ANALYTICS_LLM_MODEL', 'gpt-4o')

    def assemble_query(self, question: str, atoms: List[SemanticAtom]) -> str:
        """
        Takes the user question and the retrieved atoms, and generates SQL.
        """
        if not atoms:
            return "ERROR: No semantic atoms found to answer this question."

        context = self._build_context(atoms)
        
        system_prompt = (
            "You are a specialized SQL Compiler. Your task is to generate a PostgreSQL query "
            "based on a user question using ONLY the provided SQL snippets (Semantic Atoms).\n\n"
            "### RULES:\n"
            "1. Use ONLY the table names, column names, and snippets provided in the context.\n"
            "2. DO NOT invent new columns or tables. If information is missing, FAIL.\n"
            "3. If the user asks for something not covered by the atoms, fail gracefully by returning "
            "'ERROR: Logic not found for [concept]'.\n"
            "4. Ensure the SQL is valid PostgreSQL.\n"
            "5. Combine metrics and joins logic accurately.\n"
            "6. Return ONLY the SQL query, no explanation.\n"
        )
        
        user_prompt = f"User Question: {question}\n\nAvailable Semantic Atoms:\n{context}"
        
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0
            )
            
            sql = response.choices[0].message.content.strip()
            # Remove markdown formatting if present
            if sql.startswith("```"):
                lines = sql.splitlines()
                # Remove first and last line if they are markers
                if lines[0].startswith("```"): lines = lines[1:]
                if lines[-1].startswith("```"): lines = lines[:-1]
                sql = "\n".join(lines).strip()
            
            return sql
        except Exception as e:
            return f"ERROR: LLM Service failure: {str(e)}"

    def _build_context(self, atoms: List[SemanticAtom]) -> str:
        """Formats atoms into a readable context for the LLM."""
        atoms_list = []
        for atom in atoms:
            atoms_list.append(
                f"- Name: {atom.name}\n"
                f"  Type: {atom.atom_type}\n"
                f"  Description: {atom.description}\n"
                f"  SQL Snippet: {atom.sql_snippet}\n"
            )
        return "\n".join(atoms_list)
