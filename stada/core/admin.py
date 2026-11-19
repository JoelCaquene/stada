from django.contrib import admin, messages
from django.utils import timezone
from django.utils.safestring import mark_safe
from django.db.models import Sum
from .models import (
    CustomUser, PlatformSettings, Level, BankDetails, Deposit,
    Withdrawal, Task, Roulette, UserLevel, PlatformBankDetails,
    PromoCode, PromoCodeUsage

# --- CONFIGURAÇÕES DO USUÁRIO ---

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    # Adicionado 'total_convidados_n1' e 'total_investido_equipe' ao list_display
    list_display = ('phone_number', 'available_balance', 'total_convidados_n1', 'total_investido_equipe', 'free_days_count', 'is_staff', 'is_active', 'date_joined')
    search_fields = ('phone_number', 'invite_code')
    list_filter = ('is_staff', 'is_active', 'level_active')
    ordering = ('-date_joined',)
    list_editable = ('free_days_count',)

    def total_convidados_n1(self, obj):
        """Conta quantos usuários foram convidados diretamente (Nível 1)"""
        count = CustomUser.objects.filter(invited_by=obj).count()
        return f"{count} pessoas"
    total_convidados_n1.short_description = 'Convidados (N1)'

    def total_investido_equipe(self, obj):
        """Soma o valor total de depósitos aprovados dos convidados de Nível 1"""
        total = Deposit.objects.filter(
            user__invited_by=obj, 
            is_approved=True
        ).aggregate(Sum('amount'))['amount__sum'] or 0.00
        return f"{total:,.2f} $"
    total_investido_equipe.short_description = 'Total Investido (N1)'

@admin.register(PlatformBankDetails)
class PlatformBankDetailsAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_holder_name', 'IBAN', 'random_code')
    search_fields = ('bank_name', 'account_holder_name', 'IBAN', 'random_code')
    fields = ('bank_name', 'account_holder_name', 'IBAN', 'random_code')


# --- CONFIGURAÇÕES DE DEPÓSITO (COM SOMA AUTOMÁTICA E VALIDAÇÃO DE 30 MINUTOS) ---
@admin.register(Deposit)
class DepositAdmin(admin.ModelAdmin):
    list_display = (
        'user',
        'amount_usd',
        'payment_method',
        'random_code',
        'tx_hash',
        'is_approved',
        'is_expired',
        'tempo_30_min',
        'created_at',
        'proof_link',
    )
    search_fields = ('user__phone_number', 'payer_name', 'random_code', 'tx_hash')
    list_filter = ('is_approved', 'is_expired', 'payment_method', 'created_at')

    readonly_fields = ('current_proof_display', 'created_at', 'tempo_30_min')
    fieldsets = (
        ('Informações do Usuário e Pagamento ($)', {
            'fields': ('user', 'amount', 'payment_method', 'payer_name', 'random_code', 'tx_hash')
        }),
        ('Status e Aprovação (Prazo de 30 Minutos)', {
            'fields': ('is_approved', 'is_expired', 'tempo_30_min', 'created_at')
        }),
        ('Visualização do Comprovativo', {
            'fields': ('current_proof_display',),
        }),
    )

    def amount_usd(self, obj):
        return f"${obj.amount} USD"
    amount_usd.short_description = 'Valor ($)'

    def tempo_30_min(self, obj):
        if obj.is_approved:
            return mark_safe('<span style="color: #16a34a; font-weight: bold;">Aprovado (Contagem encerrada)</span>')
        if not obj.created_at:
            return "—"
        elapsed = int((timezone.now() - obj.created_at).total_seconds())
        remaining = (30 * 60) - elapsed
        if remaining <= 0 or getattr(obj, 'is_expired', False):
            return mark_safe('<span style="color: #dc2626; font-weight: bold;">Expirado / Falso (00:00)</span>')
        mins, secs = divmod(remaining, 60)
        return mark_safe(f'<span style="color: #d97706; font-weight: bold;">Restam {mins:02d}:{secs:02d}</span>')
    tempo_30_min.short_description = 'Prazo 30 Min'

    def save_model(self, request, obj, form, change):
        """
        Lógica para somar o saldo automaticamente ao aprovar dentro de 30 minutos.
        Se passar dos 30 minutos sem aprovação prévia, marca como expirado/falso e não credita.
        """
        if change:
            old_obj = Deposit.objects.get(pk=obj.pk)
            if not old_obj.is_approved and obj.is_approved:
                elapsed = int((timezone.now() - obj.created_at).total_seconds()) if obj.created_at else 0
                if elapsed > (30 * 60):
                    obj.is_approved = False
                    if hasattr(obj, 'is_expired'):
                        obj.is_expired = True
                    super().save_model(request, obj, form, change)
                    messages.error(
                        request,
                        f"Tempo de 30 minutos esgotado para o depósito #{obj.id}. Marcado como falso/expirado e NÃO creditado."
                    )
                    return

                if hasattr(obj, 'is_expired'):
                    obj.is_expired = False
                user = obj.user
                user.available_balance += obj.amount
                user.save()
                messages.success(request, f"Saldo de ${obj.amount} USD adicionado a {user.phone_number}!")

        super().save_model(request, obj, form, change)

    def proof_link(self, obj):
        if obj.proof_of_payment:
            return mark_safe(f'<a href="{obj.proof_of_payment.url}" target="_blank" style="color: #2e7d32; font-weight: bold;">Ver Imagem</a>')
        return "Nenhum"
    proof_link.short_description = 'Comprovativo'

    def current_proof_display(self, obj):
        if obj.proof_of_payment:
            return mark_safe(f'''
                <div style="margin-bottom: 10px;">
                    <a href="{obj.proof_of_payment.url}" target="_blank" class="button" style="background: #0056b3; color: white; padding: 5px 10px; text-decoration: none; border-radius: 4px;">Abrir em ecrã inteiro</a>
                </div>
                <img src="{obj.proof_of_payment.url}" style="max-width: 450px; height: auto; border: 2px solid #ddd; border-radius: 8px;" />
            ''')
        return "Nenhum Comprovativo Carregado"
    current_proof_display.short_description = 'Foto do Comprovativo'

# --- CONFIGURAÇÕES DE SAQUE ---

@admin.register(Withdrawal)
class WithdrawalAdmin(admin.ModelAdmin):
    list_display = ('user', 'amount', 'status', 'dados_bancarios_cliente', 'created_at')
    search_fields = ('user__phone_number', 'withdrawal_details')
    list_filter = ('status', 'method', 'created_at')
    list_editable = ('status',)
    
    fieldsets = (
        ('Informações de Solicitação', {
            'fields': ('user', 'amount', 'status')
        }),
        ('Dados para Pagamento', {
            'fields': ('method', 'withdrawal_details', 'dados_completos_perfil'),
        }),
        ('Datas', {
            'fields': ('created_at',),
        }),
    )
    readonly_fields = ('created_at', 'dados_completos_perfil')

    def dados_bancarios_cliente(self, obj):
        try:
            return obj.user.bank_details.IBAN
        except:
            return mark_safe('<span style="color: red;">Não cadastrado</span>')
    dados_bancarios_cliente.short_description = 'IBAN (Perfil)'

    def dados_completos_perfil(self, obj):
        try:
            dados = obj.user.bank_details
            return mark_safe(f"""
                <div style="background: #f8f9fa; padding: 10px; border: 1px solid #ccc;">
                    <strong>Banco:</strong> {dados.bank_name}<br>
                    <strong>IBAN:</strong> {dados.IBAN}<br>
                    <strong>Titular:</strong> {dados.account_holder_name}
                </div>
            """)
        except:
            return "O cliente ainda não preencheu os dados bancários no perfil."
    dados_completos_perfil.short_description = 'Dados Bancários no Perfil'

# --- SISTEMA DE SORTEIO (CUPONS) ---

@admin.register(PromoCode)
class PromoCodeAdmin(admin.ModelAdmin):
    list_display = ('code', 'value', 'is_active', 'created_at')
    search_fields = ('code',)
    list_editable = ('is_active', 'value')

@admin.register(PromoCodeUsage)
class PromoCodeUsageAdmin(admin.ModelAdmin):
    list_display = ('user', 'promo_code', 'prize_won', 'used_at')
    list_filter = ('used_at', 'promo_code')
    search_fields = ('user__phone_number', 'promo_code__code')

# --- NÍVEIS E PLATAFORMA ---

@admin.register(PlatformSettings)
class PlatformSettingsAdmin(admin.ModelAdmin):
    list_display = ('id', 'whatsapp_link')

@admin.register(Level)
class LevelAdmin(admin.ModelAdmin):
    list_display = ('name', 'deposit_value', 'daily_gain', 'monthly_gain', 'cycle_days')
    search_fields = ('name',)

@admin.register(PlatformBankDetails)
class PlatformBankDetailsAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_holder_name', 'IBAN')

# --- TAREFAS E HISTÓRICO ---

@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ('user', 'earnings', 'task_day', 'completed_at')
    list_filter = ('task_day', 'completed_at')

@admin.register(UserLevel)
class UserLevelAdmin(admin.ModelAdmin):
    list_display = ('user', 'level', 'purchase_date', 'is_active')

@admin.register(Roulette)
class RouletteAdmin(admin.ModelAdmin):
    list_display = ('user', 'prize', 'spin_date')

@admin.register(BankDetails)
class BankDetailsAdmin(admin.ModelAdmin):
    list_display = ('user', 'bank_name', 'account_holder_name', 'IBAN')
    