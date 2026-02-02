from django.db import models
from pgvector.django import VectorField

class BaseSemanticAtom(models.Model):
    ATOM_TYPES = [
        ('METRIC', 'Metric'),
        ('DIMENSION', 'Dimension'),
        ('JOIN', 'Join'),
    ]
    
    name = models.CharField(max_length=255, unique=True)
    description = models.TextField()
    sql_snippet = models.TextField()
    atom_type = models.CharField(max_length=20, choices=ATOM_TYPES)
    embedding = VectorField(dimensions=1536, null=True, blank=True)  # Standard OpenAI dimension
    
    # Metadata for dependencies (e.g., a metric might require specific joins)
    dependencies = models.ManyToManyField(
        'self', 
        symmetrical=False, 
        blank=True, 
        related_name='required_by'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ['name']

    def __str__(self):
        return f"{self.name} ({self.atom_type})"

    def save(self, *args, **kwargs):
        if not self.embedding:
            from .services.retriever import VectorService
            try:
                # Create a rich representation for embedding
                text_to_embed = f"{self.name}: {self.description}"
                service = VectorService()
                self.embedding = service.get_embedding(text_to_embed)
            except Exception:
                # Fail gracefully if LLM service is down/misconfigured
                pass
        super().save(*args, **kwargs)

class SemanticAtom(BaseSemanticAtom):
    class Meta(BaseSemanticAtom.Meta):
        verbose_name = "Semantic Atom"
        verbose_name_plural = "Semantic Atoms"

class BaseVerifiedQuery(models.Model):
    question = models.TextField()
    sql_query = models.TextField()
    is_approved = models.BooleanField(default=True)
    embedding = VectorField(dimensions=1536, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if not self.embedding:
            from .services.retriever import VectorService
            try:
                service = VectorService()
                self.embedding = service.get_embedding(self.question)
            except Exception:
                pass
        super().save(*args, **kwargs)

class VerifiedQuery(BaseVerifiedQuery):
    class Meta(BaseVerifiedQuery.Meta):
        verbose_name = "Verified Query"
        verbose_name_plural = "Verified Queries"

class FailedQuery(models.Model):
    question = models.TextField()
    attempted_sql = models.TextField(null=True, blank=True)
    error_message = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Failed Query"
        verbose_name_plural = "Failed Queries"

    def __str__(self):
        return f"Failed: {self.question[:50]}..."
