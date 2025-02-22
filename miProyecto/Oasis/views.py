from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.contrib import messages
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.response import Response
from rest_framework import status
from rest_framework.authtoken.models import Token
from django.urls import reverse

from django.db.models import F
from collections import defaultdict



# Para tomar el from desde el settings
from django.conf import settings
from django.core.mail import BadHeaderError, EmailMessage
# Importamos todos los modelos de la base de datos
from django.db import IntegrityError, transaction
from django.http import JsonResponse
import json

from django.utils import timezone

#APIVIEW
from rest_framework.views import APIView



from rest_framework import viewsets

from .serializers import *
from rest_framework import viewsets

#Importar el crypt
from .crypt import *


#Importar todos los modelos de la base de datos.
from .models import *

def index(request):
    logueo = request.session.get("logueo", False)
    if logueo == False:
        print(logueo)
        return render(request, "Oasis/index.html")
    else:
        return redirect("inicio")

def login(request):
    if request.method == "POST":
        user = request.POST.get("correo")
        password = request.POST.get("clave")
		#Select * from Usuario where correo = "user" and clave = "passw"
        try:
            q = Usuario.objects.get(email = user)
            if verify_password(password, q.password):
                # Crear variable de sesión.
                request.session["logueo"] = {
                    "id": q.id,
                    "nombre": q.nombre,
                    "rol": q.rol,
                    "nombre_rol":q.get_rol_display()
                }
                messages.success(request, f"Bienvendido {q.nombre}!!")
            else:
                messages.error(request, 'Error: Usuario o contraseña incorrectos...')
            return redirect("inicio")
        except Exception as e:
            messages.error(request, f"Error: Usuario o contraseña incorrectos {e}")
            return redirect("index")
    else:
        messages.warning(request, "Error: No se enviaron datos.")
        return redirect("index")


def logout(request):
	try:
		del request.session["logueo"]
		del request.session["carrito"]
		messages.success(request, "Sesión cerrada correctamente")
		return redirect("index")
	except Exception as e:
		#messages.warning(request, "No se pudo cerrar sesión")
		return redirect("inicio")
    
def inicio(request):
    logueo = request.session.get("logueo", False)
    if logueo:
        try:
            usuario_id = request.session['logueo']['id']
            usuario = Usuario.objects.get(pk=usuario_id)
            contexto = {'data': usuario}
            return render(request, "Oasis/index.html", contexto)
        except Usuario.DoesNotExist:
            messages.error(request, "El usuario no existe")
    else:
        return redirect("index")

def registro(request):
    return render(request, 'Oasis/registro/registro.html')


def crear_usuario_registro(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        email = request.POST.get('email')
        cedula = request.POST.get('cedula')
        fecha_nacimiento = request.POST.get('fechaNacimiento')
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')

        if password1 != password2:
            messages.error(request, "Las contraseñas no coinciden")
            return redirect("registro")
        else:
            try:
                q = Usuario.objects.create(
                    nombre = nombre,
                    fecha_nacimiento = fecha_nacimiento,
                    email = email,
                    cedula = cedula,
                    password = hash_password(password1)
                )
                q.save()
                messages.success(request, "Usuario creado exitosamente")
            except Exception as e:
                messages.error(request, f"Error: {e}")

    return redirect("registro")


#TÉRMINOS Y CONDICIONES
def terminos_condiciones(request):
    return render(request, 'Oasis/terminos_condiciones/tyc.html')

#PERFIL
def ver_perfil(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    logueo = request.session.get("logueo", False)
    #Consultamos en base de datos el ID del usuario logueado
    q = Usuario.objects.get(pk = logueo["id"])
    roles = Usuario.ROLES
    estado = Usuario.ESTADO
    contexto = {'data': q, 'roles': roles, 'estado':estado, 'user':user}
    return render(request, "Oasis/login/perfil.html", contexto)

def editar_perfil(request, id):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        fecha_nacimiento = request.POST.get('fechaNacimiento')
        email = request.POST.get('email')
        cedula = request.POST.get('cedula')
        foto_nueva = request.FILES.get('foto_nueva')

        try:
            q = Usuario.objects.get(pk = id)
            q.nombre = nombre
            q.email = email
            q.fecha_nacimiento = fecha_nacimiento
            q.cedula = cedula
            
            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Usuario actualizado correctamente")
        except Exception as e:
            messages.error(request,f'Error: {e}')
    else:
        messages.warning(request,'No se enviaron datos')

    return redirect('ver_perfil')


#CAMBIAR CONTRASEÑA

def cambiar_clave(request):
    if request.method == "POST":
        logueo = request.session.get("logueo", False)
        q = Usuario.objects.get(pk=logueo["id"])

        c1 = request.POST.get("nueva1")
        c2 = request.POST.get("nueva2")

        #Puedes intentar cambiando "Clave" por "Password" - Sale un error diferente. JAJAJA
        if verify_password(request.POST.get("clave"), q.password):
            if c1 == c2:
                #Cambiar clave en DB
                q.password = hash_password(c1)
                q.save()
                del request.session["logueo"]
                del request.session["carrito"]
                messages.success(request, "Contraseña cambiada correctamente!")
                return redirect("index")
            else:
               messages.info(request, "Las contraseñas nuevas no coinciden...")
        else:
            messages.error(request, "Contraseña no válida...")
    else:
        messages.warning(request, "Error: No se enviaron datos...")
    
    return redirect('cc_formulario')

def entradas_usuario(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    entrada = CompraEntrada.objects.filter(usuario = logueo["id"])

    if not entrada:
        contexto = {'entrada_info': None, 'user': user}
        return render(request, "Oasis/usuario/entradas.html", contexto)

    evento_info = [Evento.objects.get(id=entrada.evento.id) for entrada in entrada]
    
    entradas_info = []
    for entrada, evento in zip(entrada, evento_info):
        entradas_info.append({'entrada': entrada, 'evento': evento})

    contexto = {'entrada_info': entradas_info, 'user': user}
    return render(request, "Oasis/usuario/entradas.html", contexto)

def entradas_usuario_info(request, id):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk=logueo["id"])
    
    try:
        entrada = CompraEntrada.objects.get(pk=id, usuario=logueo["id"])
        evento = Evento.objects.get(pk=entrada.evento.id)

        total_personas = entrada.entrada_general + entrada.entrada_vip
        
        contexto = {'entrada': entrada, 'evento': evento, 'total_personas': total_personas,  'user': user}
        return render(request, "Oasis/usuario/entradas_info.html", contexto)
    except CompraEntrada.DoesNotExist:
        messages.error(request, f'La compra de entrada con el ID {id} no existe o no pertenece al usuario actual.')
        return redirect('entradas_usuario')
    
def reservas_usuario(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    reserva = Reserva.objects.filter(usuario = logueo["id"])

    if not reserva:
        contexto = {'reservas_info': None, 'user': user}
        return render(request, "Oasis/usuario/reservas.html", contexto)

    evento_info = [Evento.objects.get(id=reserva.evento.id) for reserva in reserva]
    
    reservas_info = []
    for reserva, evento in zip(reserva, evento_info):
        reservas_info.append({'reserva': reserva, 'evento': evento})

    contexto = {'reservas_info': reservas_info, 'user': user}
    return render(request, "Oasis/usuario/reservas.html", contexto)

def reservas_usuario_info(request, id):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk=logueo["id"])
    
    try:
        reserva = Reserva.objects.get(pk=id, usuario=logueo["id"])
        evento = Evento.objects.get(pk=reserva.evento.id)
        
        contexto = {'reserva': reserva, 'evento': evento, 'user': user}
        return render(request, "Oasis/usuario/reservas_info.html", contexto)
    except CompraEntrada.DoesNotExist:
        messages.error(request, f'La compra de entrada con el ID {id} no existe o no pertenece al usuario actual.')
        return redirect('reservas_usuario')


#USUARIOS
def guInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Usuario.objects.all()
    usuarioAdmin = Usuario.objects.filter(rol=1).count()
    usuarioBartender = Usuario.objects.filter(rol=2).count()
    usuarioMesero = Usuario.objects.filter(rol=3).count()
    usuarioCliente = Usuario.objects.filter(rol=4).count()
    contexto = {'data': q, 
    'user': user, 
    'roles':Usuario.ROLES, 
    'estado':Usuario.ESTADO,
    'clientes':usuarioCliente, 
    'administradores':usuarioAdmin, 
    'bartenders':usuarioBartender, 
    'meseros':usuarioMesero,
    'url': "Gestion_Usuarios" 
    }
    return render(request, "Oasis/usuarios/guInicio.html", contexto)

def guUsuariosBloqueados(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    contexto = {'user':user, 'url':'Usuarios_Bloqueados'}
    return render(request, "Oasis/usuarios/guUsuariosBloqueados.html", contexto)

def guUsuariosCrear(request):
    if request.method == 'POST':
        try:
            nombre = request.POST.get('nombre')
            fecha_nacimiento = request.POST.get('fechaNacimiento')
            email = request.POST.get('email')
            password = request.POST.get('password')
            cedula = request.POST.get('cedula')
            foto = request.FILES.get('foto')
            rol = int(request.POST.get('rol'))
            estado = int(request.POST.get('Estado'))

            if foto is None:
                foto = "Img_usuarios/default.png"
            
            q = Usuario(
                nombre=nombre,
                fecha_nacimiento=fecha_nacimiento,
                email=email,
                password=hash_password(password),
                rol=rol,
                cedula=cedula,
                estado=estado,
                foto=foto,
            )

            q.save()
            messages.success(request, "Usuario creado correctamente")
        except Exception as e:
            messages.error(request, f'Error: {e}')
    else:
        messages.warning(request, 'No se enviaron datos')

    return redirect('guInicio')

def guUsuariosEliminados(request, id):
    try:
        q = Usuario.objects.get(pk = id)
        q.delete()
        messages.success(request, 'Usuario eliminado correctamente!!')
    except Exception as e:
        messages.error(request,f'Error: {e}')

    return redirect('guInicio')


def guUsuariosActualizar(request, id):
    if request.method == 'POST':
        nombre = request.POST.get('nombre')
        fecha_nacimiento = request.POST.get('fechaNacimiento')
        email = request.POST.get('email')
        # password = request.POST.get('password')
        cedula = request.POST.get('cedula')
        rol = request.POST.get('rol')
        estado = request.POST.get('Estado')
        foto_nueva = request.FILES.get('foto_nueva')

        try:
            q = Usuario.objects.get(pk=id)
            q.nombre = nombre
            q.email = email
            # q.password = hash_password(password)
            q.fecha_nacimiento = fecha_nacimiento
            q.rol = rol
            q.cedula = cedula
            q.estado = estado
            
            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Usuario actualizado correctamente")
        except Exception as e:
            messages.error(request,f'Error: {e}')
    else:
        messages.warning(request,'No se enviaron datos')

    return redirect('guInicio')


#PRODUCTOS

def invProductos(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Producto.objects.all()
    categories = Categoria.objects.all()
    contexto = {'data' : q, 'user':user,  'categories':categories}
    return render(request, "Oasis/inventario/invProductos.html", contexto)

def crearProducto(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('nombre')
            desc = request.POST.get('descripcion')
            cat_id = int(request.POST.get('categoria'))
            inventario = int(request.POST.get('inventario'))
            pre = request.POST.get('precio')
            foto = request.FILES.get('foto')

            cat = Categoria.objects.get(pk=cat_id)
            
            if foto == None:
                foto = "Img_productos/default.png"

            q = Producto(
                nombre=nom,
                descripcion=desc,
                categoria=cat,
                inventario=inventario,
                precio=pre,
                foto=foto,
            )
            q.save()
            messages.success(request, "Producto Agregado Correctamente!")
        except Exception as e:
            messages.error(request, f'Error: {e}')
    else:
        messages.warning(request, f'Error: No se enviaron datos...')

    return redirect('Productos')

def eliminarProducto(request, id):
    try:
        q = Producto.objects.get(pk = id)
        q.delete()
        messages.success(request, "Producto Eliminado Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('Productos')

def actualizarProducto(request, id):
    if request.method == "POST":
        cat = Categoria.objects.get(pk=request.POST.get('categoria'))
        nom = request.POST.get('nombre')
        desc = request.POST.get('descripcion')
        inventario = int(request.POST.get('inventario'))
        precio_str = request.POST.get('precio')
        precio_str = precio_str.replace(',', '.')
        pre = float(precio_str)
        foto_nueva = request.FILES.get('foto_nueva')

        try:
            q = Producto.objects.get(pk=id)
            q.nombre = nom
            q.categoria = cat
            q.descripcion = desc
            q.inventario = inventario
            q.precio = pre

            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Producto Actualizado Correctamente!")

        except Exception as e:
            messages.error(request, f'Error: {e}')

    else:
        messages.warning(request, f'Error: No se enviaron datos...')

    return redirect('Productos')



def peInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk=logueo["id"])

    pedidos = Pedido.objects.all().order_by('-fecha')

    detalles_pedidos = []
    for pedido in pedidos:
        detalles = DetallePedido.objects.filter(pedido=pedido)
        detalles_activos_count = detalles.filter(estado='Activo').count()
        detalles_pedidos.append({
            'pedido': pedido,
            'detalles': detalles,
            'detalles_activos_count': detalles_activos_count
        })

    total_preparacion = 0
    for pedido in pedidos:
        if pedido.estado == pedido.PREPARACION:
            total_preparacion += 1

    contexto = {
        'user': user,
        'detalles_pedidos': detalles_pedidos,
        'total_preparacion': total_preparacion,
    }
    return render(request, "Oasis/pedidos/peInicio.html", contexto)

def peGestionMesas(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    mesas = Mesa.objects.all()
    mesas_activas = Mesa.objects.filter(estado='Activa').count()
    mesas_disponibles = Mesa.objects.filter(estado='Disponible').count()
    contexto = {'user':user, 'mesas':mesas, 'mesas_activas': mesas_activas, 'mesas_disponibles':mesas_disponibles}
    return render (request, "Oasis/pedidos/peGestionMesas.html", contexto)

def pedidoEmpleado(request, id):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk=logueo["id"])
    carrito = request.session.get("carrito", [])
    mesa = Mesa.objects.get(pk=id)
    productos = Producto.objects.all()
    contexto = {'user': user, 'productos': productos, 'mesa': mesa, 'carrito': carrito}
    return render(request, "Oasis/pedidos/pedidoEmpleado.html", contexto)

#MESAS

def mesaInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Mesa.objects.all()
    contexto = {'data' : q , 'user':user}
    return render(request, "Oasis/mesas/mesasInicio.html", contexto)

def crearMesa(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('nombre')
            cap = int(request.POST.get('capacidad'))
            precio = int(request.POST.get('precio'))
            
            if Mesa.objects.filter(nombre=nom).count() == 0:
                if 4 <= cap <= 8:
                    q = Mesa(
                    nombre = nom,
                    capacidad = cap,
                    precio = precio,
                    usuario = ""
                    )
                    q.save()
                    messages.success(request, "Mesa Registrada Correctamente!")
                else:
                    messages.warning (request, f'Incorrecto: La capacidad de cada mesa debe ser mayor a 4 o menor a 8.')
            else:
                messages.warning (request, f'Incorrecto: Esta mesa ya esta creada en el sistema.')
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('Mesas')
    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        return redirect('Mesas')

def mesaActualizar(request, id):
    if request.method == "POST":
        nom = request.POST.get('nombre')
        cap = int(request.POST.get('capacidad'))
        precio = int(request.POST.get('precio'))
        try:
            if Mesa.objects.filter(nombre=nom).exclude(pk=id).exists():
                messages.warning(request, f'Incorrecto: Esta mesa ya está creada en el sistema con otro ID.')
            elif cap > 9 or cap < 4:
                messages.warning (request, f'Incorrecto: La capacidad de cada mesa debe ser mayor a 4 o menor a 8')
            else:
                q = Mesa.objects.get(pk=id)
                q.nombre = nom
                q.capacidad = cap
                q.precio = precio
                q.save()
                messages.success(request, "Mesa Actualizada Correctamente!")
        except Exception as e:
            messages.error(request, f'Error: {e}')

    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        
    return redirect('Mesas')

def eliminarMesa(request, id):
    try:
        q = Mesa.objects.get(pk = id)
        q.delete()
        messages.success(request, "Mesa Eliminada Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('Mesas')



#EVENTOS

def eveInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Evento.objects.all()
    contexto = {'data' : q, 'user':user}
    return render(request, "Oasis/eventos/eveInicio.html", contexto)


def crearEvento(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('nombre')
            date = request.POST.get('fecha')
            time = request.POST.get('hora_incio')
            general = request.POST.get('entrada_general')
            vip = request.POST.get('entrada_vip')
            aforo = request.POST.get('aforo')
            desc = request.POST.get('descripcion')
            flyer = request.FILES.get('flyer')

            if flyer == None:
                flyer = "Img_eventos/default.png"

            # INSERT INTO Evento VALUES (nom, date, time, desc, foto)
            q = Evento(
                nombre = nom,
                fecha = date,
                hora_incio = time,
                precio_entrada = general,
                precio_vip = vip,
                aforo = aforo,
                descripcion = desc,
                foto = flyer
            )
            q.save()
            messages.success(request, "Evento Creado Correctamente!")
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('Eventos')
    
    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        return redirect('Eventos')

def eliminarEvento(request, id):
    try:
        evento = Evento.objects.get(pk=id)
        if CompraEntrada.objects.filter(evento=evento).exists():
            messages.warning(request, f'Incorrecto: No se puede eliminar este evento porque tiene entradas vendidas.')
        else:
            evento.delete()
            messages.success(request, "Evento Eliminado Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('Eventos')

def actualizarEvento(request, id):
    if request.method == "POST":
        nom = request.POST.get('nombre')
        date = request.POST.get('fecha')
        time = request.POST.get('hora_incio')
        general = request.POST.get('entrada_general')
        vip = request.POST.get('entrada_vip')
        aforo = request.POST.get('aforo')
        desc = request.POST.get('descripcion')
        foto_nueva = request.FILES.get('foto_nueva')
        try:
            q = Evento.objects.get(pk=id)
            q.nombre = nom
            q.fecha = date
            q.hora_incio = time
            q.precio_entrada = general
            q.precio_vip = vip
            q.aforo = aforo
            q.descripcion = desc

            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Evento Actualizado Correctamente!")

        except Exception as e:
            messages.error(request, f'Error: {e}')

    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        
    return redirect('Eventos')

def eveEntradas(request, id):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    evento = Evento.objects.get(pk = id)
    entradas = CompraEntrada.objects.filter(evento = id)

    correos = [Usuario.objects.get(nombre=entrada.usuario).email for entrada in entradas]
    
    entradas_con_correo = []
    for entrada, correo in zip(entradas, correos):
        entradas_con_correo.append({'entrada': entrada, 'correo': correo})

    contexto = {'evento': evento, 'user':user, 'entradas': entradas_con_correo}

    return render(request, 'Oasis/eventos/eveEntradas.html', contexto)

def eliminarEntrada(request, id):
    try:
        entrada = CompraEntrada.objects.get(pk=id)
        entrada.delete()
        evento = Evento.objects.filter(pk=entrada.evento.id).first()
        evento.entradas_disponibles = F('entradas_disponibles') + entrada.entrada_general + entrada.entrada_vip
        evento.save()
        messages.success(request, "Entrada Eliminada Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('Eventos')


def eveReserva(request, id):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk=logueo["id"])
    evento = Evento.objects.get(id=id)
    reservas = Reserva.objects.filter(evento=evento)

    reservas_info = []
    for reserva in reservas:
        reserva_info = {
            'reserva': reserva,
            'mesa_reservada': reserva.mesa,
        }
        reservas_info.append(reserva_info)

    todas_las_mesas = Mesa.objects.all()

    mesas_reservadas = [reserva.mesa for reserva in reservas]

    mesas_no_reservadas = [mesa for mesa in todas_las_mesas if mesa not in mesas_reservadas]

    total_reservadas = len(mesas_reservadas)

    contexto = {
        'user': user,
        'evento': evento,
        'totalReservadas': total_reservadas,
        'reservasInfo': reservas_info,
        'mesasNoReservadas': mesas_no_reservadas
    }

    return render(request, 'Oasis/eventos/eveReserva.html', contexto)


# MENÚ (CATEGORÍAS)
def meInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Categoria.objects.all()
    contexto = {'data' : q, 'user':user}
    return render(request, "Oasis/menu/meInicio.html", contexto)


def crearCategoria(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('nombre')
            desc = request.POST.get('descripcion')
            foto = request.FILES.get('foto')

            if foto == None:
                foto = "Img_categorias/default.jpg"

            # INSERT INTO Categoria VALUES (nom, desc)
            q = Categoria(
                nombre = nom, 
                descripcion = desc,
                foto = foto,
                )
            q.save()
            messages.success(request, "Categoria Creada Correctamente!")
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('Menu')
    
    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        return redirect('Menu')

def eliminarCategoria(request, id):
    try:
        q = Categoria.objects.get(pk = id)
        q.delete()
        messages.success(request, "Categoria Eliminada Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('Menu')


def actualizarCategoria(request, id):
    if request.method == "POST":
        nom = request.POST.get('nombre')
        desc = request.POST.get('descripcion')
        foto_nueva = request.FILES.get('foto_nueva')
        try:
            q = Categoria.objects.get(pk=id)
            q.nombre = nom
            q.descripcion = desc

            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Categoria Actualizada Correctamente!")

        except Exception as e:
            messages.error(request, f'Error: {e}')

    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        
    return redirect('Menu')

def meProductos(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    contexto = {'user':user}
    return render (request, 'Oasis/menu/meProductos.html', contexto)



def gaInicio(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    q = Galeria.objects.all()
    contexto = {'data' : q, 'user':user}
    return render(request, "Oasis/galeria/gaInicio.html", contexto)



def crearCarpeta(request):
    if request.method == "POST":
        try:
            nom = request.POST.get('nombre')
            date = request.POST.get('fecha')
            foto = request.FILES.get('foto')

            if foto == None:
                foto = "Img_carpeta/default.png"

            # INSERT INTO Evento VALUES (nom, date, time, desc, foto)
            q = Galeria(
                nombre = nom,
                fecha = date,
                foto = foto,
            )
            q.save()
            messages.success(request, "Carpeta Creada Correctamente!")
        except Exception as e:
            messages.error(request, f'Error: {e}')
        return redirect('gaInicio')
    
    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        return redirect('gaInicio')

def eliminarCarpeta(request, id):
    try:
        q = Galeria.objects.get(pk = id)
        q.delete()
        messages.success(request, "Carpeta Eliminada Correctamente!")
    except Exception as e:
        messages.error(request, f'Error: {e}')
    
    return redirect('gaInicio')


def actualizarCarpeta(request, id):
    if request.method == "POST":
        nom = request.POST.get('nombre')
        date = request.POST.get('fecha')
        foto_nueva = request.FILES.get('foto_nueva')
        try:
            q = Galeria.objects.get(pk=id)
            q.nombre = nom
            q.fecha = date
            
            if foto_nueva:
                q.foto = foto_nueva

            q.save()
            messages.success(request, "Carpeta Actualizada Correctamente!")

        except Exception as e:
            messages.error(request, f'Error: {e}')

    else:
        messages.warning (request, f'Error: No se enviaron datos...')
        
    return redirect('gaInicio')


def gaFotos(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])
    contexto = {'user':user}
    return render(request, 'Oasis/galeria/gaFotos.html', contexto)



def front_productos(request):
    logueo = request.session.get("logueo", False)
    user = None
    if logueo:
        user = Usuario.objects.get(pk = logueo["id"])
    categorias = Categoria.objects.all()

    cat = request.GET.get("cat")

    if cat == None:
        productos = Producto.objects.all()
    else:
        c = Categoria.objects.get(pk=cat)
        productos = Producto.objects.filter(categoria=c)
    
    contexto = {"data": user,"productos": productos, "categorias": categorias}
    return render(request, "Oasis/front_productos/front_productos.html", contexto)


def front_eventos(request):
    logueo = request.session.get("logueo", False)
    user = None
    if logueo:
        user = Usuario.objects.get(pk = logueo["id"])
    eventos = Evento.objects.all()

    contexto = {"data": user, "eventos": eventos}
    return render(request, "Oasis/front_eventos/front_eventos.html", contexto)

def front_eventos_info(request, id):
    logueo = request.session.get("logueo", False)
    user = None
    if logueo:
        user = Usuario.objects.get(pk = logueo["id"])
    evento = Evento.objects.get(pk=id)
    reservas = Reserva.objects.filter(evento=evento)
    mesas = Mesa.objects.all()

    listMesas = []

    for reserva in reservas:
        listMesas.append(reserva.mesa)

    total_defecto = evento.precio_entrada + evento.precio_vip

    contexto = {"data": user, "evento": evento, "mesas": mesas, "total_defecto": total_defecto, "listMesas": listMesas}
    return render(request, "Oasis/front_eventos/front_eventos_info.html", contexto)

def comprar_entradas(request, id):
    logueo = request.session.get("logueo", False)
    messages = []

    if not logueo:
        messages.append({'message_type': 'warning', 'message': 'Inicia sesión antes de comprar'})
        return JsonResponse({'messages': messages}) 

    user = Usuario.objects.get(pk=logueo["id"])
    evento = Evento.objects.get(pk=id)

    if request.method == "POST":    
        data = json.loads(request.body)
        
        cantidad_general = int(data.get("cantidad_general", 0))
        cantidad_vip = int(data.get("cantidad_vip", 0))
        precio_entrada_general = evento.precio_entrada
        precio_entrada_vip = evento.precio_vip
        total = (cantidad_general * precio_entrada_general) + (cantidad_vip * precio_entrada_vip)

        if evento.entradas_disponibles >= cantidad_general + cantidad_vip:
            compra = CompraEntrada.objects.create(
                usuario=user, 
                evento=evento,
                entrada_general=cantidad_general,
                entrada_vip=cantidad_vip,
                total=total
            )

            evento.entradas_disponibles -= cantidad_general + cantidad_vip
            evento.save()

            messages.append({'message_type': 'success', 'message': 'Entradas compradas correctamente'})
        else:
            messages.append({'message_type': 'error', 'message': 'No hay suficientes entradas disponibles'})

    return JsonResponse({'messages': messages})


def reservar_mesa(request, id):
    logueo = request.session.get("logueo", False)
    messages = []

    if not logueo:
        messages.append({'message_type': 'warning', 'message': 'Inicia sesión antes de comprar'})
        return JsonResponse({'messages': messages}) 

    user = Usuario.objects.get(pk=logueo["id"])
    evento = Evento.objects.get(pk=id)

    if request.method == "POST":
        data = json.loads(request.body)

        mesa = Mesa.objects.get(pk=data.get("id_mesa", 0))
        total = int(data.get("total_general", 0))
        if evento.entradas_disponibles >= mesa.capacidad:
            reserva = Reserva.objects.create(
                usuario=user, 
                evento=evento,  
                mesa=mesa,
                total=total,
            )
            evento.entradas_disponibles -= mesa.capacidad
            if evento.reservas == False:
                evento.reservas = True
            evento.save()
            mesa.estado_reserva = 'Reservada'
            mesa.save()

            messages.append({'message_type': 'success', 'message': 'Mesa reservada correctamente'})
        else:
            messages.append({'message_type': 'error', 'message': 'No hay suficientes entradas disponibles'})

    return JsonResponse({'messages': messages}) 


def escanear_mesa (request):
    logueo = request.session.get("logueo", False)
    user = None
    if logueo:
        user = Usuario.objects.get(pk = logueo["id"])

    mesas = Mesa.objects.all()

    contexto = {'data':user, 'mesas':mesas}
    return render(request, "Oasis/front_pedidos/escanear_mesa.html", contexto)


def pedidoUsuario(request, id):
    logueo = request.session.get("logueo", False)
    user = None
    if logueo:
        user = get_object_or_404(Usuario, pk=logueo["id"])

    mesa = get_object_or_404(Mesa, pk=id)
    carrito = request.session.get("carrito", [])
    productos = Producto.objects.all()

    contexto = {'data': user, 'productos': productos, 'mesa': mesa, 'carrito': carrito}
    return render(request, "Oasis/front_pedidos/pedido_usuario.html", contexto)
    

def carrito_add(request):
    if request.method == "POST":
        try:
            carrito = request.session.get("carrito", [])
            if not carrito:
                request.session["carrito"] = []
                request.session["items"] = 0
                carrito = []

            id_producto = int(request.POST.get("id"))
            cantidad = int(request.POST.get("cantidad", 1))
            template_name = request.POST.get("template_name", "Oasis/carrito/carrito.html")
            # Consulto en DB
            q = Producto.objects.get(pk=id_producto)

            for p in carrito:
                if p["id"] == id_producto:
                    if q.inventario >= (p["cantidad"] + cantidad) and cantidad > 0:
                        p["cantidad"] += cantidad
                        p["subtotal"] = p["cantidad"] * q.precio
                    else:
                        messages.warning(request, "Cantidad supera inventario")
                    break
            else:
                if q.inventario >= cantidad and cantidad > 0:
                    carrito.append({
                        "id": q.id,
                        "foto": q.foto.url,
                        "producto": q.nombre,
                        "precio": q.precio,
                        "cantidad": cantidad,
                        "subtotal": cantidad * q.precio
                    })
                else:
                    messages.warning(request, "No se puede agregar, no hay suficiente inventario.")

            # Actualizamos variable de sesión carrito...
            request.session["carrito"] = carrito
            items = len(carrito)
            contexto = {
                "items": items,
                "total": sum(p["subtotal"] for p in carrito)
            }
            request.session["items"] = len(carrito)
            return render(request, template_name, contexto)
        except ValueError:
            messages.error(request, "Error: Digite un valor correcto para cantidad...")
            return HttpResponse("Error...")
        except Exception as e:
            messages.error(request, f"Ocurrió un error: {e}")
            return HttpResponse("Error...")
    else:
        messages.warning(request, "No se enviaron datos.")
        return HttpResponse("Error...")


def carrito_ver(request):
    carrito = request.session.get("carrito", False)
    template_name = "template_name", "Oasis/carrito/carrito.html"

    if not carrito:
        request.session["carrito"] =[]
        request.session["items"] = 0
        contexto = {
        "items": 0,
        "total": 0
    }
    else:
        contexto = {
            "items": len(carrito),
            "total": sum(p["subtotal"] for p in carrito)
        }
        request.session["items"] = len(carrito)
    return render(request, template_name, contexto)


def carrito_ver_admin(request):
    carrito = request.session.get("carrito", False)
    template_name = "Oasis/carrito/carrito_admin.html"

    if not carrito:
        request.session["carrito"] =[]
        request.session["items"] = 0
        contexto = {
        "items": 0,
        "total": 0
    }
    else:
        contexto = {
            "items": len(carrito),
            "total": sum(p["subtotal"] for p in carrito)
        }
        request.session["items"] = len(carrito)
    return render(request, template_name, contexto)


def carrito_eliminar(request, id):
    try:
        carrito = request.session.get("carrito", False)
        if carrito != False:
            for i, item in enumerate(carrito):
                if item["id"] == id:
                    carrito.pop(i)
                    break
            else:
                messages.warning(request, "No se encontró el item carrito")
        request.session["carrito"] = carrito
        request.session["items"] = len(carrito)
        return redirect('carrito_ver')
    except Exception as e:
        messages.error(request, f"Error: {e}")

def carrito_eliminar_admin(request, id):
    try:
        carrito = request.session.get("carrito", False)
        if carrito != False:
            for i, item in enumerate(carrito):
                if item["id"] == id:
                    carrito.pop(i)
                    break
            else:
                messages.warning(request, "No se encontró el item carrito")
        request.session["carrito"] = carrito
        request.session["items"] = len(carrito)
        return redirect('carrito_ver_admin')
    except Exception as e:
        messages.error(request, f"Error: {e}")


def vaciar_carrito(request):
	request.session["carrito"] = []
	request.session["items"] = 0
	return redirect('front_productos')

def vaciar_carrito_admin(request):
	request.session["carrito"] = []
	request.session["items"] = 0
	return redirect('pedidoEmpleado')

def actualizar_totales_carrito(request, id_producto):
    carrito = request.session.get("carrito", False)
    cantidad = request.GET.get("cantidad")
    if carrito != False:
        for i, item in enumerate(carrito):
            if item["id"] == id_producto:
                item["cantidad"] = int(cantidad)
                item["subtotal"] = int(cantidad) * item["precio"]
                break
        else:
            messages.warning(request, "No se encontró el item carrito")
    request.session["carrito"] = carrito
    request.session["items"] = len(carrito)
    return redirect('carrito_ver')

def actualizar_totales_carrito_admin(request, id_producto):
    carrito = request.session.get("carrito", False)
    cantidad = request.GET.get("cantidad")
    if carrito != False:
        for i, item in enumerate(carrito):
            if item["id"] == id_producto:
                item["cantidad"] = int(cantidad)
                item["subtotal"] = int(cantidad) * item["precio"]
                break
        else:
            messages.warning(request, "No se encontró el item carrito")
    request.session["carrito"] = carrito
    request.session["items"] = len(carrito)
    return redirect('carrito_ver_admin')


def crear_pedido_admin(request, id):
    try:
        logueo = request.session.get("logueo")
        
        user = Usuario.objects.get(pk=logueo["id"])
        mesa = Mesa.objects.get(pk=id)
        
        carrito = request.session.get("carrito", [])
        if not carrito:
            messages.error(request, "El pedido está vacío.")
            return redirect('pedidoEmpleado', id=id)
        
        comentario = request.POST.get("comentario", "")
        
        pedido = Pedido.objects.create(
            mesa=mesa, 
            total=sum(item['subtotal'] for item in carrito), 
            usuario=user,
            comentario=comentario
        )
        
        for p in carrito:
            producto = Producto.objects.get(pk=p['id'])
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=p['cantidad'],
                precio=p['precio']
            )
            producto.inventario -= p['cantidad']
            producto.save()

        mesa.estado = mesa.ACTIVA
        mesa.usuario = f"MESERO: {user.nombre}"
        mesa.save()
        request.session["carrito"] = []
        request.session["items"] = 0
        messages.success(request, "Pedido creado con éxito.")

    except Exception as e:
        messages.error(request, f"Ocurrió un Error: {e}")
    
    return redirect('peGestionMesas')


class token_qr(APIView):
    def post(self, request):
        try:
            mesa = MesaSerializer(codigo_qr = request.data.mesa)
            user = UsuarioSerializer(email=request.data.email)
            if serializer.is_valid(mesa):
                mesa.estado = mesa.ACTIVA
                mesa.usuario = user.email
                mesa.save()
                return JsonResponse({'mesa':{
                    'nombre': mesa.nombre,
                    'qr':mesa.qr
                }})
        except Exception as e:
            return JsonResponse({'Error':f'{e}'}, status=400)



def crear_pedido_usuario(request, id):
    try:
        logueo = request.session.get("logueo", False)
        user = None
        if logueo:
            user = Usuario.objects.get(pk = logueo["id"])

        else:
            messages.error(request, "Inicia sesión ó registrate para realizar el pedido.")
            return redirect('pedidoUsuario', id=id)
        
        mesa = Mesa.objects.get(pk=id)
        
        carrito = request.session.get("carrito", [])
        if not carrito:
            messages.error(request, "El pedido está vacío.")
            return redirect('pedidoEmpleado', id=id)
        
        comentario = request.POST.get("comentario", "")
        
        pedido = Pedido.objects.create(
            mesa=mesa, 
            total=sum(item['subtotal'] for item in carrito), 
            usuario=user,
            comentario=comentario
        )
        
        for p in carrito:
            producto = Producto.objects.get(pk=p['id'])
            DetallePedido.objects.create(
                pedido=pedido,
                producto=producto,
                cantidad=p['cantidad'],
                precio=p['precio']
            )
            producto.inventario -= p['cantidad']
            producto.save()

        mesa.estado = mesa.ACTIVA
        mesa.usuario = user.email
        mesa.save()
        request.session["carrito"] = []
        request.session["items"] = 0
        messages.success(request, "Pedido creado con éxito.")

    except Exception as e:
        messages.error(request, f"Ocurrió un Error: {e}")
    
    return redirect('ver_detalles_pedido_usuario')




def pagar_pedido(request, id, rol):
    try:
        mesa = Mesa.objects.get(pk=id)
        # Filtrar pedidos excluyendo los cancelados
        pedidos = Pedido.objects.filter(mesa=mesa).exclude(estado='Cancelado')
        pedidos_eliminados = Pedido.objects.filter(mesa=mesa).filter(estado='Cancelado')

        if not pedidos.exists():
            if rol == 'usuario':
                messages.error(request, "No hay pedidos para esta mesa.")
                return redirect('ver_detalles_pedido_usuario')
            else:
                messages.error(request, "No hay pedidos para esta mesa.")
                return redirect('peGestionMesas')

        usuario = pedidos.first().usuario

        # Verificar si algún pedido está en preparación
        if any(pedido.estado == pedido.PREPARACION for pedido in pedidos):
            if rol == 'usuario':
                messages.warning(request, "No se pueden pagar pedidos en preparación.")
                return redirect('ver_detalles_pedido_usuario')
            else:
                messages.warning(request, "No se pueden pagar pedidos en preparación.")
                return redirect('ver_pedidos_mesa', mesa_id=id)

        # Calcular el total del pedido excluyendo los productos eliminados
        total_pedido = sum(
            sum(detalle.cantidad * detalle.precio for detalle in pedido.detallepedido_set.filter(estado='Activo'))
            for pedido in pedidos
        )

        # Crear el historial de pedido
        historial_pedido = HistorialPedido.objects.create(
            mesa=mesa,
            fecha=timezone.now(),
            usuario=usuario,
            total=total_pedido
        )

        # Agrupar productos por ID y sumar las cantidades, excluyendo los productos eliminados
        productos_agrupados = defaultdict(lambda: {'cantidad': 0, 'precio': 0})
        for pedido in pedidos:
            for detalle in pedido.detallepedido_set.filter(estado='Activo'):
                producto_id = detalle.producto.id
                productos_agrupados[producto_id]['cantidad'] += detalle.cantidad
                productos_agrupados[producto_id]['precio'] = detalle.precio

        # Crear objetos en la tabla de historial de detalles con los productos agrupados
        for producto_id, datos in productos_agrupados.items():
            producto = Producto.objects.get(pk=producto_id)
            HistorialDetallePedido.objects.create(
                historial_pedido=historial_pedido,
                producto=producto,
                cantidad=datos['cantidad'],
                precio=datos['precio']
            )

        # Eliminar pedidos y detalles originales
        pedidos.delete()
        pedidos_eliminados.delete()

        # Actualizar el estado de la mesa
        mesa.estado = mesa.DISPONIBLE
        mesa.usuario = ""
        mesa.save()

        messages.success(request, "¡Pedido pagado exitosamente!")
    except Exception as e:
        messages.error(request, f"Ocurrió un Error: {e}")

    if rol == 'usuario':
        return redirect('ver_detalles_pedido_usuario')
    else:
        return redirect('peGestionMesas')


def ver_pedidos_mesa(request, mesa_id):
    mesa = Mesa.objects.get(pk=mesa_id)
    pedidos = Pedido.objects.filter(mesa=mesa)

    detalles_pedidos = []
    cuenta = 0

    for pedido in pedidos:
        detalles = DetallePedido.objects.filter(pedido=pedido)
        subtotal_pedido = 0

        for detalle in detalles:
            if detalle.estado != detalle.ELIMINADO:
                subtotal_pedido += detalle.subtotal
        
        detalles_pedidos.append({
            'pedido': pedido,
            'detalles': detalles,
        })

        if pedido.estado != 'Cancelado':
            cuenta += subtotal_pedido

    pedidos_eliminados = len(pedidos.filter(estado='Cancelado'))
    total_pedidos = len(pedidos)

    contexto = {
        'mesa': mesa,
        'detalles_pedidos': detalles_pedidos,
        'total_pedidos': total_pedidos,
        'pedidos_eliminados': pedidos_eliminados,
        'cuenta': cuenta
    }
    return render(request, 'Oasis/pedidos/info_pedido_mesa.html', contexto)


def ver_historial_pedidos(request):
    logueo = request.session.get("logueo", False)
    user = Usuario.objects.get(pk = logueo["id"])

    historial_pedidos = HistorialPedido.objects.all().order_by('-fecha')

    detalles_pedidos = []
    for historial_pedido in historial_pedidos:
        detalles = HistorialDetallePedido.objects.filter(historial_pedido=historial_pedido)
        detalles_pedidos.append({
            'pedido': historial_pedido,
            'detalles': detalles
        })

    contexto = {
        'user':user, 'detalles_pedidos': detalles_pedidos, 
    }
    return render(request, "Oasis/pedidos/peHistorial.html", contexto)


def entregar_pedido(request, id):
    try:
        pedido = Pedido.objects.get(pk=id)
        pedido.estado = pedido.ENTREGADO
        pedido.save()
        messages.success(request, "El pedido ha sido entregado.")
    except Exception as e:
        messages.error(request, f"Ocurió un un Error: {e}")

    return redirect('peInicio')


def cancelar_pedido(request):
    if request.method == 'POST':
        pedido_id = request.POST.get('pedido_id')
        comentario = request.POST.get('comentario')
        try:
            pedido = Pedido.objects.get(pk=pedido_id)
            pedido.comentario = comentario
            pedido.estado = pedido.CANCELADO
            pedido.save()
            messages.success(request, "Pedido cancelado exitosamente.")
        except Pedido.DoesNotExist:
            messages.error(request, "El pedido no existe.")
        except Exception as e:
            messages.error(request, f"Ocurrio un error: {e}")
    return redirect('peInicio')


def eliminar_item(request):
    if request.method == 'POST':
        producto_id = request.POST.get('producto_id')
        motivo = request.POST.get('comentario')
        
        try: 
            detalle = DetallePedido.objects.get(pk=producto_id)
            detalle.motivo_eliminacion = motivo
            detalle.estado = detalle.ELIMINADO
            detalle.save()
            
            messages.success(request, 'Producto eliminado del pedido con éxito.')

        except DetallePedido.DoesNotExist:
            messages.error(request, "El detalle del pedido no existe.")
        except Exception as e:
            messages.error(request, f'Ocurrió un error: {e}')
    
    return redirect('peInicio')

def liberar_mesa(request, id):
    try:
        mesa = Mesa.objects.get(pk=id)
        mesa.estado = mesa.DISPONIBLE
        mesa.usuario = ""
        mesa.save()
        messages.success(request, "Mesa liberada exitosamente.")
    except Exception as e:
        messages.error(request, f"Ocurrio un error: {e}")

    return redirect('peGestionMesas')


def crear_venta(request):
	try:
		logueo = request.session.get("logueo")

		user = Usuario.objects.get(pk=logueo["id"])
		nueva_venta = Venta.objects.create(usuario=user)

		carrito = request.session.get("carrito", [])
		for p in carrito:
			producto = Producto.objects.get(pk=p["id"])
			cantidad = p["cantidad"]

			detalle_venta = DetalleVenta.objects.create(
                venta=nueva_venta,
                producto= producto,
                cantidad= cantidad,
                precio_historico=producto.precio,
            )

			producto.inventario -= cantidad
			producto.save()

			request.session["carrito"] = []
			request.session["items"] = 0

		messages.success(request, "Venta realizada correctamente!")

	except Exception as e:
		messages.error(request, f"Ocurrió un Error: {e}")

	return redirect('inicio')

def ver_pedidos_usuario(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(pk=logueo["id"])
    historial_pedidos = HistorialPedido.objects.filter(usuario=user).order_by('-fecha')

    detalles_pedidos = []
    for historial_pedido in historial_pedidos:
        detalles = HistorialDetallePedido.objects.filter(historial_pedido=historial_pedido)
        detalles_pedidos.append({
            'pedido': historial_pedido,
            'detalles': detalles
        })

    total_pedidos = historial_pedidos.count()
        
    contexto = {
        'user':user, 'detalles_pedidos': detalles_pedidos, 'total_pedidos': total_pedidos
    }
    return render(request, "Oasis/usuario/pedidos_usuario.html", contexto)

def ver_detalles_usuario(request):
    logueo = request.session.get("logueo")
    user = Usuario.objects.get(pk=logueo["id"])
    pedidos = Pedido.objects.filter(usuario=user).order_by('-fecha')


    try:
        mesa = Mesa.objects.get(usuario=user.email)
    except Mesa.DoesNotExist:
        mesa = None

    detalles_pedidos = []
    cuenta = 0

    for pedido in pedidos:
        detalles = DetallePedido.objects.filter(pedido=pedido)
        subtotal_pedido = 0

        for detalle in detalles:
            if detalle.estado != detalle.ELIMINADO:
                subtotal_pedido += detalle.subtotal
        
        detalles_pedidos.append({
            'pedido': pedido,
            'detalles': detalles,
        })

        if pedido.estado != 'Cancelado':
            cuenta += subtotal_pedido

    pedidos_eliminados = pedidos.filter(estado='Cancelado').count()
    total_pedidos = pedidos.count()

    contexto = {
        'user': user,
        'mesa': mesa,
        'detalles_pedidos': detalles_pedidos,
        'total_pedidos': total_pedidos,
        'pedidos_eliminados': pedidos_eliminados,
        'cuenta': cuenta
    }
    return render(request, 'Oasis/usuario/detalles_pedido_usuario.html', contexto)


# -------------------------------------------------------------------------------------------
from rest_framework.authentication import SessionAuthentication, TokenAuthentication
from rest_framework.permissions import IsAuthenticated

# Vistas para el conjunto de datos de las API

class UsuarioViewSet(viewsets.ModelViewSet):
    # authentication_classes = [TokenAuthentication, SessionAuthentication]
	authentication_classes = [TokenAuthentication]
	permission_classes = [IsAuthenticated]
	queryset = Usuario.objects.all()
	serializer_class = UsuarioSerializer

class EventoViewSet(viewsets.ModelViewSet):
    queryset = Evento.objects.all()
    serializer_class = EventoSerializer

class CompraEntradaViewSet(viewsets.ModelViewSet):
    queryset = CompraEntrada.objects.all()
    serializer_class = CompraEntradaSerializer

class MesaViewSet(viewsets.ModelViewSet):
    queryset = Mesa.objects.all()
    serializer_class = MesaSerializer

class ReservaViewSet(viewsets.ModelViewSet):
    queryset = Reserva.objects.all()
    serializer_class = ReservaSerializer

class CategoriaViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer

class ProductoViewSet(viewsets.ModelViewSet):
    queryset = Producto.objects.all()
    serializer_class = ProductoSerializer

class PedidoViewSet(viewsets.ModelViewSet):
    queryset = Pedido.objects.all()
    serializer_class = PedidoSerializer

class DetallePedidoViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

class PedidoMesaViewSet(viewsets.ModelViewSet):
    queryset = DetallePedido.objects.all()
    serializer_class = DetallePedidoSerializer

"""class InventarioViewSet(viewsets.ModelViewSet):
    queryset = Inventario.objects.all()
    serializer_class = InventarioSerializer """

class GaleriaViewSet(viewsets.ModelViewSet):
    queryset = Galeria.objects.all()
    serializer_class = GaleriaSerializer

class FotosViewSet(viewsets.ModelViewSet):
    queryset = Fotos.objects.all()
    serializer_class = FotosSerializer

class VentaViewSet(viewsets.ModelViewSet):
    queryset = Venta.objects.all()
    serializer_class = VentaSerializer

class DetalleVentaViewSet(viewsets.ModelViewSet):
    queryset = DetalleVenta.objects.all()
    serializer_class = DetalleVentaSerializer



# ------------------------------- Personalización de Token Autenticación ------------
from rest_framework.authtoken.views import ObtainAuthToken


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_auth_token(sender, instance=None, created=False, **kwargs):
	if created:
		Token.objects.create(user=instance)

class CustomAuthToken(ObtainAuthToken):
	def post(self, request, *args, **kwargs):
		serializer = self.serializer_class(data=request.data,
										   context={'request': request})
		serializer.is_valid(raise_exception=True)
		user = serializer.validated_data['username']
		# traer datos del usuario para bienvenida y ROL
		usuario = Usuario.objects.get(email=user)
		token, created = Token.objects.get_or_create(user=usuario)

		return Response({
			'token': token.key,
			'user': {
				'user_id': usuario.pk,
				'email': usuario.email,
				'nombre': usuario.nombre,
				'rol': usuario.rol,
				'foto': usuario.foto.url
			}
		})