from django.db import models


class TestFKModel(models.Model):
    # tell nose to ignore
    __test__ = False

    value = models.CharField(max_length=64)


class TestFKModel2(models.Model):
    # tell nose to ignore
    __test__ = False

    value = models.CharField(max_length=64)


class TestModel(models.Model):
    # tell nose to ignore
    __test__ = False

    value = models.CharField(max_length=64)
    fk = models.ForeignKey(TestFKModel, on_delete=models.CASCADE)
    fk2 = models.ForeignKey(TestFKModel2, on_delete=models.CASCADE)
    fk_m2m = models.ManyToManyField(TestFKModel, related_name='+')
