# Reviewer de continuidad

Reviewer determinístico para conflictos explícitos entre estados narrativos configurados.

- Sólo evalúa pares ordenados de marcadores declarados en el manifiesto.
- No infiere causalidad, intención, flashbacks ni transiciones implícitas.
- Produce `ReviewFinding`; nunca modifica `Work` ni crea/aplica `Patch`.
- Las reglas propias de una obra deben llegar por configuración gobernada, no por cambios en el runtime.
