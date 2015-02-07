from django.db import models


class TestFKModel(models.Model):
    value = models.CharField(max_length=64)


class TestModel(models.Model):
    value = models.CharField(max_length=64)
    fk = models.ForeignKey(TestFKModel)
