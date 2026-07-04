"""Reenvio de mensagem de recuperação pros leads pendentes.
Envia 1 mensagem a cada 3 minutos pra não estressar o WhatsApp.
"""

import sys
import time
import traceback

from app import memory, whatsapp

RECOVERY_MSG = (
    "Oi! Aqui é da MRV — desculpa a demora em responder. Tivemos uma "
    "instabilidade rapidinha no atendimento e sua mensagem pode ter "
    "ficado sem resposta. Já está tudo resolvido 🙌\n\n"
    "Você teve interesse na vaga de Engenheiro Civil? Se ficou alguma "
    "dúvida sobre a vaga ou precisa de ajuda pra fazer o cadastro no "
    "app, é só me chamar aqui que eu te ajudo!"
)

# Lista dos números extraídos dos 2 screenshots
# (5521969602779 já foi enviado no teste)
PHONES = [
    # Screenshot 1
    "553391469825",
    "557991929572",
    "554198258999",
    "5514998221510",
    "5514997828096",
    "5521967527270",
    "5517996389398",
    "554396344958",
    # Screenshot 2
    "558294012170",
    "5511971562034",
    "5519991452639",
    "559391788806",
    "558198681996",
    "559888284966",
    "5514988143209",
    "555196502319",
]

INTERVALO_SEGUNDOS = 180  # 3 minutos entre cada envio


def main() -> None:
    total = len(PHONES)
    ok = 0
    fail = 0
    print(f"Iniciando broadcast pra {total} leads. Intervalo: {INTERVALO_SEGUNDOS}s")
    print(f"Tempo estimado: {total * INTERVALO_SEGUNDOS // 60} min")
    print("-" * 60)
    for i, phone in enumerate(PHONES, 1):
        try:
            whatsapp.send_text(phone, RECOVERY_MSG)
            memory.save_message(phone, "assistant", RECOVERY_MSG)
            ok += 1
            print(f"[{i}/{total}] OK  -> {phone}", flush=True)
        except Exception as e:
            fail += 1
            print(f"[{i}/{total}] FAIL -> {phone}: {e}", flush=True)
            traceback.print_exc()
        if i < total:
            print(f"    Aguardando {INTERVALO_SEGUNDOS}s antes do próximo...", flush=True)
            time.sleep(INTERVALO_SEGUNDOS)
    print("-" * 60)
    print(f"Terminado: {ok} sucesso, {fail} falhas")


if __name__ == "__main__":
    main()
