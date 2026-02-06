from django.urls import path
from . import views
from UserManager.views import LoginAPIView, UserCreateAPIView, UserStatusAPIView ,dashboard_view
urlpatterns = [
    #path('create-user/', views.create_user, name='create_user'),
    path('', views.login, name='login'),
    path("login/", LoginAPIView.as_view(), name="login"),
    path("api/create-user/", UserCreateAPIView.as_view(), name="api_create_user"),
    path("dashboard/", dashboard_view, name="dashboard"),
    path('api/update-user-status/', UserStatusAPIView.as_view(), name='update-user-status'),
    path('get-downline/<str:role_name>/', views.get_downline_data, name='get_downline_data'),
    path('get-registration-form/', views.get_registration_form, name='get_registration_form'),
    path('api/get-creator-limits/<str:username>/', views.get_creator_limits),
    path("get-uplines/<str:role>/", views.get_upline_users),
    path(
    "accounts/edit/<str:username>/",
    views.EditAccountView.as_view(),
    name="edit_account"
)

   


]
