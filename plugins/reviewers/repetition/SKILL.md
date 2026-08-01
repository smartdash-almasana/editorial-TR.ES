# Revisor de repetición

Reviewer determinístico que inspecciona bloques de expresión y produce `ReviewFinding` cuando una frase configurada supera el mínimo de repeticiones.

No modifica la obra, no crea `Patch` y no decide por el editor. Su resultado se integra al `ReviewEngine` como cualquier otro `Reviewer` del kernel.
