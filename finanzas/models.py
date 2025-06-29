from django.db import models
from django.contrib.auth.models import User

# Create your models here.
class registro_transacciones(models.Model):
    propietario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateField()
    descripcion = models.CharField(max_length=100)
    categoria = models.CharField(max_length=100)
    monto = models.DecimalField(max_digits=65, decimal_places=3)
    TIPO_CHOICES = [
        ('INGRESO', 'Ingreso'),
        ('GASTO', 'Gasto'),
        ('TRANSFERENCIA','Transferencia'),

    ]
    tipo = models.CharField(max_length=15, choices=TIPO_CHOICES)
    cuenta_origen = models.CharField(max_length=100)
    cuenta_destino = models.CharField(max_length=100)
    id_prestamo_ref = models.CharField(max_length=10, blank=True, null=True)

    def __str__(self):
        return f"{self.id_transaccion} - {self.descripcion}"