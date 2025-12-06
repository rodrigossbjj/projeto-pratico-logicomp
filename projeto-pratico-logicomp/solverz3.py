import re
from z3 import * 

def generic_solver(variables, restrictions):
    """
    variables: dict with name -> Z3 type (e.g., {'A': Bool('A'), 'B': Bool('B')})
    restrictions: list of Z3 expressions (BoolRef)
    """
    solver = Solver()
    for r in restrictions:
        solver.add(r)

    if solver.check() == sat:
        model = solver.model()
        return {name: model[var] for name, var in variables.items()}
    elif solver.check() == unsat:
        return "Inconsistente (sem solução)"
    else:
        return "Indefinido (solver não conseguiu decidir)"
    

def parse_puzzle_to_z3(puzzle_text):
    """
    Parses simple Knights and Knaves puzzles (A, B, C, ...) and generates Z3 variables and constraints.
    Returns a tuple (variables, restrictions).
    """
    # Detect all characters that speak (e.g., A, B, C)
    names = sorted(set(re.findall(r"\b([A-Z])\s+diz:", puzzle_text)))
    if not names:
        raise ValueError("No characters found in the puzzle text.")

    # Create Z3 boolean variables: True = knight, False = knave
    variables = {n: Bool(n) for n in names}
    restrictions = []

    # Capture all statements in the format "X diz: '...'"
    statements = re.findall(r"([A-Z])\s+diz:\s*'([^']+)'", puzzle_text)
    for n, statement in statements:
        statement = statement.strip()

        # Pattern: "X é um patife"
        m = re.match(r"([A-Z])\s+é\s+um\s+patife", statement)
        if m:
            ref = m.group(1)
            restrictions.append(variables[n] == Not(variables[ref]))
            continue

        # Pattern: "X é um cavaleiro"
        m = re.match(r"([A-Z])\s+é\s+um\s+cavaleiro", statement)
        if m:
            ref = m.group(1)
            restrictions.append(variables[n] == variables[ref])
            continue

        # Pattern: "X e eu somos diferentes"
        m = re.match(r"([A-Z])\s+e\s+eu\s+somos\s+diferentes", statement)
        if m:
            ref = m.group(1)
            restrictions.append(variables[n] == (variables[n] != variables[ref]))
            continue

        # Pattern: "X e eu somos iguais"
        m = re.match(r"([A-Z])\s+e\s+eu\s+somos\s+iguais", statement)
        if m:
            ref = m.group(1)
            restrictions.append(variables[n] == (variables[n] == variables[ref]))
            continue

        # Pattern: "X e eu somos iguais"
        m = re.match(r"([A-Z])\s+e\s+([A-Z])\s+somos\s+iguais", statement)
        if m:
            ref1, ref2 = m.group(1), m.group(2)
            restrictions.append(variables[ref1] == (variables[ref1] == variables[ref2]))
            continue

        # Pattern: "X e Y são iguais"
        m = re.match(r"([A-Z])\s+e\s+([A-Z])\s+são\s+iguais", statement)
        if m:
            ref1, ref2 = m.group(1), m.group(2)
            restrictions.append(variables[n] == (variables[ref1] == variables[ref2]))
            continue

        # Pattern: "Eu sou um cavaleiro"
        if re.match(r"Eu sou um cavaleiro", statement):
            restrictions.append(variables[n] == True)
            continue

        # Pattern: "Eu sou um patife"
        if re.match(r"Eu sou um patife", statement):
            restrictions.append(variables[n] == False)
            continue

        # Pattern: "X e Y são diferentes" (X != Y)
        m = re.match(r"([A-Z])\s+e\s+([A-Z])\s+somos\s+diferentes", statement)
        if m:
            ref1, ref2 = m.group(1), m.group(2)
            # ref1 diz que ref1 e ref2 são diferentes
            restrictions.append(variables[ref1] == (variables[ref1] != variables[ref2]))
            continue

        # Pattern: "X e Y são diferentes"
        m = re.match(r"([A-Z])\s+e\s+([A-Z])\s+são\s+diferentes", statement)
        if m:
            ref1, ref2 = m.group(1), m.group(2)
            restrictions.append(variables[n] == (variables[ref1] != variables[ref2]))
            continue

    if not restrictions:
        raise ValueError("No recognizable constraints found in the puzzle.")

    return variables, restrictions



def logical_consequences(variables, restrictions):
    """
    Check which variables (people) have their value logically determined
    by the puzzle constraints.
    Returns a dict: { 'A': 'Knight' | 'Scoundrel' | 'Undetermined' }
    """
    results = {}
    
    for name, var in variables.items():
        s1 = Solver()
        s1.add(restrictions)
        s1.add(Not(var))  # Testa se pode ser falso
        can_be_false = (s1.check() == sat)
        
        s2 = Solver()
        s2.add(restrictions)
        s2.add(var)  # Testa se pode ser verdadeiro
        can_be_true = (s2.check() == sat)
        
        if can_be_true and not can_be_false:
            results[name] = "Cavaleiro (necessariamente verdadeiro)"
        elif can_be_false and not can_be_true:
            results[name] = "Patife (necessariamente falso)"
        elif can_be_true and can_be_false:
            results[name] = "Indeterminado (pode ser ambos)"
        else:
            results[name] = "Inconsistente (sem modelo possível)"
    
    return results
