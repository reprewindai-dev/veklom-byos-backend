import z3

def check_action_safety(country: str, age: int, identity_score: float, is_authorized: bool) -> tuple[bool, str]:
    """
    Uses the Z3 SMT Solver to prove that an agent's proposed action meets the
    sovereign compliance axioms and least-privilege security boundaries.
    """
    s = z3.Solver()

    # Define logical variables
    Sanctioned = z3.Bool('Sanctioned')
    Underage = z3.Bool('Underage')
    BiometricScore = z3.Real('BiometricScore')
    Authorized = z3.Bool('Authorized')

    # Assign state values
    sanctioned_countries = ["RU", "IR", "KP", "SY"]
    s.add(Sanctioned == (country.upper() in sanctioned_countries))
    s.add(Underage == (age < 18))
    s.add(BiometricScore == float(identity_score))
    s.add(Authorized == is_authorized)

    # Core Compliance Axioms
    # 1. Action MUST NOT originate from a sanctioned country.
    # 2. Representative MUST NOT be underage.
    # 3. Biometric Verification Score MUST exceed the 0.80 safety baseline.
    # 4. Action MUST be human-authorized.
    compliance_axiom = z3.And(
        z3.Not(Sanctioned),
        z3.Not(Underage),
        BiometricScore >= 0.80,
        Authorized == True
    )

    s.add(compliance_axiom)

    # Prove satisfiability
    if s.check() == z3.sat:
        return True, "SATISFIABLE (SAT) - Z3 proof verify successful."
    else:
        return False, "UNSATISFIABLE (UNSAT) - Vetoed by ePCA safety axiom. Execution terminated."
