# Adversarial Cases

These are plausible customer inputs that could break or confuse a multimodal renovation extraction pipeline.

## Case 1: Contradictory voice note and photos

### Input

- Voice note says: “Create two staff showers in the back room.”
- Photos show what looks like an existing finished bathroom with one shower already installed.
- Drawing shows only one small room and no clear second shower location.

### Why this is adversarial

The system may incorrectly assume the existing visible shower is one of the requested new showers, or it may reduce the scope from two showers to one because the photos only show one.

### Expected behavior

The final scope should keep the explicit request for two showers, but add a must-have clarification:

- whether the visible shower is existing or new
- where the second shower should be located
- whether demolition/removal of existing fixtures is required

Pricing should remain `not_ready`.

---

## Case 2: Ambiguous dimension units in a hand-drawn plan

### Input

- Contractor text says: “Build a 2m placo wall.”
- Drawing contains values like `240`, `80`, `120`, and `2.60`, but no units.
- Photos show a narrow corridor where those dimensions may not fit.

### Why this is adversarial

The model may treat every visible number as centimeters or meters without enough evidence, then produce false quantities.

### Expected behavior

The drawing parser should preserve visible dimension labels but avoid using them as pricing-grade measurements unless units and segment mapping are clear.

The final scope should ask for:

- confirmed wall length
- confirmed room dimensions
- confirmed unit system
- measured opening sizes

Pricing should remain `not_ready`.

---

## Case 3: Customer asks for outcome, not scope

### Input

Customer message:

> “We need this space to be ready for staff to shower after shifts. Make it compliant and cheap. You can see the photos.”

Photos show plumbing pipes, stored furniture, old wall finishes, and a possible drain. No drawing is provided.

### Why this is adversarial

The customer describes the desired outcome but not the actual work package. The model may invent tasks such as tiling, waterproofing, electrical upgrades, or drainage rerouting without confirmation.

### Expected behavior

The system should extract the business goal but avoid turning assumptions into confirmed scope.

It should produce clarifying questions for:

- number of showers
- fixture package
- waterproofing and finishes
- hot/cold water supply
- drainage route
- electrical/water heater requirements
- who clears the room before work

Pricing should remain `not_ready` until scope is explicit.
