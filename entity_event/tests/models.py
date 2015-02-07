from django.db import models


class TestFKModel(models.Model):
    value = models.CharField(max_length=64)


class TestFKModel2(models.Model):
    value = models.CharField(max_length=64)


class TestModel(models.Model):
    value = models.CharField(max_length=64)
    fk = models.ForeignKey(TestFKModel)
    fk2 = models.ForeignKey(TestFKModel2)
    fk_m2m = models.ManyToManyField(TestFKModel, related_name='+')
