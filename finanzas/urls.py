from . import views
from django.urls import path
# Importamos las vistas de autenticación que Django nos regala
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('', views.home, name='home'),
    path('transacciones/', views.crear_transacciones, name='crear_transacciones'),
    path('registrousuarios/', views.registro, name='registro_usuarios'),
    path('login/', auth_views.LoginView.as_view(template_name='iniciosesion.html'), name='login'),
    # La LogoutView ahora usará automáticamente la variable LOGOUT_REDIRECT_URL de settings.py
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('dashboard/', views.vista_dashboard, name='dashboard'),
    path('listatransacciones/', views.lista_transacciones, name='lista_transacciones'),
    path('api/datos-gastos-categoria/', views.datos_gastos_categoria, name='api_datos_gastos'),
    path('api/datos-flujo-dinero/', views.datos_flujo_dinero, name='api_flujo_dinero'),
]