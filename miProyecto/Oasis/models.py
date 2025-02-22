from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from django.contrib.auth.models import AbstractUser

from .authentication import CustomUserManager
import uuid



# Create your models here.
class Usuario(AbstractUser):    
    username = None                                                                                                                                                                                                                                                                                                                                    
    nombre = models.CharField(max_length=254)
    email = models.EmailField(max_length=254, unique=True)
    password = models.CharField(max_length=254)
    cedula = models.CharField(max_length=10, unique=True)
    fecha_nacimiento = models.DateField()
    ROLES = (
        (1, "Administrador"),
        (2, "Bartender"),
        (3, "Mesero"),
        (4, "Cliente"),
    )
    rol = models.IntegerField(choices=ROLES, default=4)
    ESTADO = (
        (1, "Activo"),
        (2, "Bloqueado"),
    )
    estado = models.IntegerField(choices=ESTADO, default=1)
    foto = models.ImageField(upload_to="Img_usuarios/", default="Img_usuarios/default.png", blank=True)
    token_recuperar = models.CharField(max_length=254, default="", blank=True, null=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["nombre", "cedula", "fecha_nacimiento"]
    objects = CustomUserManager()


    def __str__(self):
        return self.nombre

class Evento(models.Model):
    nombre = models.CharField(max_length=150)
    fecha = models.DateField()
    hora_incio = models.TimeField() 
    descripcion = models.TextField()
    aforo = models.IntegerField(default=500)
    entradas_disponibles = models.IntegerField(default=500)
    precio_entrada = models.IntegerField(default=50000)
    precio_vip = models.IntegerField(default=75000)
    reservas = models.BooleanField(default=False)
    foto = models.ImageField(upload_to="Img_eventos/", default="Img_eventos/default.png")

    def __str__(self):
        return self.nombre
    
@receiver(post_save, sender=Evento)
def actualizar_entradas_disponibles(sender, instance, created, **kwargs):
    if created:
        instance.entradas_disponibles = instance.aforo
        instance.save()
    
class CompraEntrada(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, default=None)
    evento = models.ForeignKey(Evento, on_delete=models.CASCADE)
    entrada_general = models.IntegerField(default=1)
    entrada_vip = models.IntegerField(default=1)
    total = models.IntegerField(default=0)
    fecha_compra = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.id}'


codigo_qr = str(uuid.uuid4())

class Mesa(models.Model):
    ACTIVA = 'Activa'
    DISPONIBLE = 'Disponible'

    ESTADO_CHOICES = (
        (ACTIVA, 'Activa'),
        (DISPONIBLE, 'Disponible'),
    )

    RESERVADA = 'Reservada'
    DISPONIBLE = 'Disponible'

    RESERVA_CHOICES = (
        (RESERVADA, 'Reservada'),
        (DISPONIBLE, 'Disponible'),
    )
    nombre = models.CharField(max_length=300)
    capacidad = models.IntegerField(default=5)
    precio = models.IntegerField(default=1000000)
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=DISPONIBLE)
    estado_reserva = models.CharField(max_length=10, choices=RESERVA_CHOICES , default=DISPONIBLE)
    codigo_qr = models.CharField(max_length=100, unique=True)
    usuario = models.CharField(max_length=50, default="")

    def __str__(self):
        return f'{self.id}'

    def save(self, *args, **kwargs):
        if not self.codigo_qr:
            self.codigo_qr = str(uuid.uuid4())
        super().save(*args, **kwargs)

class Reserva(models.Model):
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, default=None)
    evento = models.ForeignKey(Evento, on_delete=models.DO_NOTHING)
    mesa = models.ForeignKey(Mesa, on_delete=models.DO_NOTHING)
    fecha_compra = models.DateTimeField(auto_now_add=True)
    total = models.IntegerField(default=0)
    codigo_qr = models.CharField(max_length=100, unique=True)
    def __str__(self):
        return f'Mesa: {self.mesa} - Evento: {self.evento.nombre}'

    def save(self, *args, **kwargs):
        if not self.codigo_qr:
            self.codigo_qr = str(uuid.uuid4())
        super().save(*args, **kwargs)

class Categoria(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    foto = models.ImageField(upload_to="Img_categorias/", default="Img_categorias/default.png")

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    nombre = models.CharField(max_length=150)
    descripcion = models.TextField()
    inventario = models.IntegerField(default=0)
    foto = models.ImageField(upload_to="Img_productos/", default="Img_productos/default.png")
    categoria = models.ForeignKey(Categoria, on_delete=models.DO_NOTHING)
    precio = models.IntegerField()

    def __str__(self):
        return self.nombre

class Pedido(models.Model):
    mesa = models.ForeignKey(Mesa, on_delete=models.DO_NOTHING)
    fecha = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, default=None)
    comentario = models.TextField(default="")
    PREPARACION = 'En preparación'
    ENTREGADO = 'Entregado'
    CANCELADO = 'Cancelado'

    ESTADO_CHOICES = (
        (PREPARACION, 'En preparacion'),
        (ENTREGADO, 'Entregado'),
        (CANCELADO, 'Cancelado')
    )

    estado = models.CharField(max_length=14, choices=ESTADO_CHOICES, default=PREPARACION)
    total = models.IntegerField(default=0)

    def __str__(self):
        return f'Pedido {self.id} - Mesa {self.mesa.nombre}'


class DetallePedido(models.Model):
    ACTIVO = 'Activo'
    ELIMINADO = 'Eliminado'
    ESTADO_CHOICES = (
        (ACTIVO, 'Activo'),
        (ELIMINADO, 'Eliminado')
    )

    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio = models.IntegerField()
    estado = models.CharField(max_length=10, choices=ESTADO_CHOICES, default=ACTIVO)
    motivo_eliminacion = models.TextField(blank=True, default='')

    @property
    def subtotal(self):
        return self.cantidad * self.precio

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'


class HistorialPedido(models.Model):
    mesa = models.ForeignKey(Mesa, on_delete=models.DO_NOTHING)
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE)
    fecha = models.DateTimeField()
    PAGADO = 'Pagado'
    CANCELADO = 'Cancelado'

    ESTADO_CHOICES = (
        (PAGADO, 'Pagado'),
        (CANCELADO, 'Cancelado')
    )
    estado = models.CharField(max_length=14, choices=ESTADO_CHOICES, default=PAGADO)
    total = models.IntegerField()

    def __str__(self):
        return f'Historial Pedido {self.id} - Mesa {self.mesa.nombre}'

class HistorialDetallePedido(models.Model):
    historial_pedido = models.ForeignKey(HistorialPedido, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.DO_NOTHING)
    cantidad = models.IntegerField()
    precio = models.IntegerField()

    @property
    def subtotal(self):
        return self.cantidad * self.precio

    def __str__(self):
        return f'{self.cantidad} x {self.producto.nombre}'

class Galeria(models.Model):
    nombre = models.CharField(max_length=254)
    fecha = models.DateField()
    foto = models.ImageField(upload_to="Img_carpeta/", default="Img_carpeta/default.png")


class Fotos(models.Model):
    foto = models.ImageField(upload_to="Img_galeria/", default="Img_galeria/default.png")
    carpeta = models.ForeignKey(Galeria, on_delete=models.DO_NOTHING)

class Venta(models.Model):
	fecha_venta = models.DateTimeField(auto_now=True)
	usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, default=None)
	ESTADOS = (
		(1, 'Pendiente'),
		(2, 'Enviado'),
		(3, 'Rechazada'),
	)
	estado = models.IntegerField(choices=ESTADOS, default=1)

	def __str__(self):
		return f"{self.id} - {self.usuario}"


class DetalleVenta(models.Model):
	venta = models.ForeignKey(Venta, on_delete=models.DO_NOTHING)
	producto = models.ForeignKey(Producto, on_delete=models.DO_NOTHING)
	cantidad = models.IntegerField()
	precio_historico = models.IntegerField()

	def __str__(self):
		return f"{self.id} - {self.venta}"

"""
# ---------------------------------------------------------------------------------
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token

@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
    if created:
        Token.objects.create(user=instance)
"""
