from django.db import models

class pokemon(models.Model):
    number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    typePokemon = models.CharField(max_length=50)
    image = models.CharField(max_length=100)
    description = models.CharField(max_length=100)

    def __str__(self):
        return self.name


# Create your models here.
