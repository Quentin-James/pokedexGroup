from django.db import models

class pokemon(models.Model):
    number = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=100)
    typePokemon = models.CharField(max_length=50)
    image = models.CharField(max_length=100)
    description = models.CharField(max_length=100)
    hp = models.IntegerField(default=0)
    attack = models.IntegerField(default=0)
    defense = models.IntegerField(default=0)
    special_attack = models.IntegerField(default=0)
    special_defense = models.IntegerField(default=0)
    speed = models.IntegerField(default=0)

    def __str__(self):
        return self.name


# Create your models here.
