from decimal import Decimal
from datetime import datetime
from django.db.models import Sum
from django.http import JsonResponse
from .forms import TransaccionesForm
from .models import registro_transacciones
from django.contrib.auth import login
from django.shortcuts import render, redirect
from .forms import FormularioRegistroPersonalizado
from django.contrib.auth.decorators import login_required

def home(request):
    return render(request, 'index.html')

def iniciosesion(request):
    return render(request, 'dashboard.html')

def registro(request):
    if request.method == 'POST':
        form = FormularioRegistroPersonalizado(request.POST)

        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('dashboard') # Redirigimos a la URL con nombre 'inicio'
    # Si el método NO es POST (es GET, una visita normal)...
    else:
        # Creamos un formulario vacío
        form = FormularioRegistroPersonalizado()
    
    # Preparamos el contexto y renderizamos la plantilla
    # Esta parte se ejecuta en ambos casos: GET o POST inválido
    context = {'form': form}
    return render(request, 'registro.html', context)

@login_required
def vista_dashboard(request):
 # Obtenemos el año y mes actual como punto de partida
    current_year = datetime.now().year
    current_month = datetime.now().month

    # Revisamos si el usuario está filtrando por un mes y año específicos
    # request.GET.get(...) busca un parámetro en la URL, ej: /dashboard?year=2024&month=5
    year = int(request.GET.get('year', current_year))
    month = int(request.GET.get('month', current_month))

    # Filtramos las transacciones por el usuario logueado, año y mes
    transacciones = registro_transacciones.objects.filter(
        propietario=request.user, 
        fecha__year=year, 
        fecha__month=month
    )
    
    # Obtenemos los diccionarios de la base de datos
    # La línea completa y corregida
    ingresos = transacciones.filter(tipo='INGRESO').exclude(categoria='Ahorro').filter(cuenta_origen = 'Efectivo Quincena').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    gastos = transacciones.filter(tipo='GASTO').exclude(categoria='Ahorro').filter(cuenta_origen = 'Efectivo Quincena').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    #disponible_banco = gastos = transacciones.filter(tipo='GASTO').exclude(categoria='Ahorro').exclude(categoria='Ahorro').filter(cuenta_origen = 'Efectivo Quincena').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    transferencias = transacciones.filter(tipo='TRANSFERENCIA').exclude(categoria='Ahorro').exclude(categoria='Ahorro').filter(cuenta_origen = 'Efectivo Quincena').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # --- DEPURACIÓN CON PRINT (VERSIÓN FINAL) ---
    print("--- INICIANDO DEPURACIÓN DE VALORES FINALES ---")
    print(f"Valor de 'ingresos': {ingresos} (Tipo: {type(ingresos)})")
    print(f"Valor de 'gastos': {gastos} (Tipo: {type(gastos)})")
    print("---------------------------------------------")
    # ----------------------------------------------------
    
    # Esta es la línea que da el error
    balance = ingresos - gastos
    disponible_banco = ingresos - gastos - transferencias
    # Preparamos el contexto para enviarlo a la plantilla
    context = {
        'ingresos': ingresos,
        'gastos': gastos,
        'balance': balance,
        'transferencias':transferencias,
        'disponible_banco':disponible_banco,
        #'ahorro': ahorro,
        'selected_year': year,
        'selected_month': month,
        'years': range(current_year, current_year - 5, -1), # Para el dropdown de años
        'months': range(1, 13) # Para el dropdown de meses
    }

    return render(request, 'dashboard.html', context)

@login_required
# Create your views here.
def crear_transacciones(request):
    if request.method == 'POST':
        form = TransaccionesForm(request.POST)

        if form.is_valid():
            # --- AQUÍ ESTÁ LA LÓGICA CORREGIDA ---

            # 1. Crea el objeto en memoria, pero NO lo guardes en la DB todavía.
            nueva_transaccion = form.save(commit=False)

            # 2. Asigna el usuario actual (que está en request.user) como propietario.
            #    El decorador @login_required se asegura de que request.user siempre exista.
            nueva_transaccion.propietario = request.user

            # 3. Ahora sí, guarda el objeto completo en la base de datos.
            nueva_transaccion.save()

            # Redirigimos al dashboard.
            return redirect('dashboard')
    else: 
        form = TransaccionesForm()

    context = {
        'form': form
    }

    return render(request, 'transacciones.html', context)

@login_required
def lista_transacciones(request):
    # La lógica de filtros es idéntica a la del dashboard
    current_year = datetime.now().year
    current_month = datetime.now().month
    year = int(request.GET.get('year', current_year))
    month = int(request.GET.get('month', current_month))

    # Obtenemos las transacciones del mes y las ordenamos por fecha
    transacciones_del_mes = registro_transacciones.objects.filter(
        propietario=request.user,
        fecha__year=year,
        fecha__month=month
    ).order_by('-fecha') # order_by('-fecha') las ordena de más reciente a más antigua

    context = {
        'transacciones': transacciones_del_mes
    }

    return render(request, 'lista_transacciones.html', context)

@login_required
def datos_gastos_categoria(request):
    # La lógica de filtros es la misma que en el dashboard
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # ¡AQUÍ ESTÁ LA NUEVA MAGIA DEL ORM!
    # Agrupamos las transacciones por 'categoria' y sumamos el 'monto' de cada una.
    gastos_por_categoria = TransaccionesFormgastos_por_categoria = registro_transacciones.objects.filter(
        propietario=request.user,
        tipo='GASTO',
        fecha__year=year,
        fecha__month=month
    ).values(
        'categoria'  # Agrupar por este campo
    ).annotate(
        total=Sum('monto') # Para cada grupo, sumar los montos y llamar al resultado 'total'
    ).order_by('-total') # Ordenar de mayor a menor gasto

    # Preparamos los datos en un formato simple para JavaScript
    data = {
        'labels': [item['categoria'] for item in gastos_por_categoria],
        'data': [item['total'] for item in gastos_por_categoria],
    }

    # Devolvemos los datos como una respuesta JSON
    return JsonResponse(data)

@login_required
def datos_flujo_dinero(request):
    # La lógica de filtros es idéntica
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))

    # Obtenemos las transacciones del mes
    transacciones_del_mes = registro_transacciones.objects.filter(
        propietario=request.user,
        fecha__year=year,
        fecha__month=month
    )

    # Calculamos el total de ingresos y gastos para ese mes
    # Usamos la misma lógica de exclusión que en nuestro dashboard
    ingresos = transacciones_del_mes.filter(tipo='INGRESO').exclude(categoria='Ahorro').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')
    gastos = transacciones_del_mes.filter(tipo='GASTO').exclude(categoria='Ahorro').aggregate(total=Sum('monto'))['total'] or Decimal('0.00')

    # Preparamos los datos en un formato simple para el gráfico
    data = {
        'labels': ['Ingresos del Mes', 'Gastos del Mes'],
        'data': [ingresos, gastos],
    }

    return JsonResponse(data)