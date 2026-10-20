"""Sample project: a ready-made 30-slide deck.

"Food Safety and Hygiene Management in Hospital Canteens" — real curated
content (objectives, temperature tables, checklists, HACCP timeline, ...),
theme dark-green-gold, status "ready".
"""

from __future__ import annotations

from datetime import datetime, timezone

from schema import new_id
from generator import build_slides
from themes import get_theme

_TITLE = "Food Safety and Hygiene Management in Hospital Canteens"


def _S(title, bullets, layout, notes, **extra):
    """Shorthand for building an outline item."""
    item = {
        "title": title,
        "bullets": list(bullets),
        "layout_hint": layout,
        "notes": notes,
    }
    item.update(extra)
    return item


def _outline() -> list[dict]:
    return [
        _S(
            _TITLE,
            ["Protecting patients, staff, and visitors through safe food handling, "
             "from receiving to serving"],
            "cover",
            "Welcome the participants — canteen staff, food handlers, and supervisors. "
            "Explain that hospital patients are far more vulnerable to foodborne illness "
            "than the general public, so our standards must be higher than a regular "
            "restaurant. Outline the journey of the session.",
        ),
        _S(
            "Learning Objectives",
            [
                "Identify the major food safety hazards in a hospital canteen",
                "Apply temperature control rules at every stage of food handling",
                "Demonstrate correct personal hygiene and handwashing practice",
                "Follow cleaning, sanitation, and pest-control procedures",
                "Implement the 7 principles of HACCP in daily work",
                "Respond correctly to a suspected food safety incident",
            ],
            "checklist",
            "Read the objectives aloud and ask participants which one feels most "
            "relevant to their daily work. Tell them they will be able to do all six "
            "by the end of this session.",
        ),
        _S(
            "Why Food Safety Matters in Hospitals",
            [
                "600 million people fall ill from contaminated food every year (WHO)",
                "420,000 deaths worldwide each year are linked to foodborne disease",
                "1 in 10 people globally are affected by foodborne illness annually",
            ],
            "stats-dashboard",
            "These are World Health Organization estimates. Stress the third point: "
            "hospital patients — the elderly, children, post-surgery and "
            "immunocompromised patients — are far more likely to suffer severe outcomes. "
            "One outbreak can close a canteen and damage the hospital's reputation.",
        ),
        _S(
            "Legal & Regulatory Requirements",
            [
                "Canteen premises must be licensed by the provincial food authority "
                "(e.g., Punjab Food Authority) and display the licence",
                "Follow a HACCP-based food safety management system (ISO 22000 principles)",
                "All food handlers need valid medical fitness certificates, renewed annually",
                "Maintain inspection-ready records: temperature logs, cleaning schedules, "
                "supplier invoices",
                "Non-compliance can mean fines, sealing of premises, or licence suspension",
            ],
            "title-content",
            "Adapt the authority name to your province or country. Emphasise that "
            "inspectors can arrive unannounced — compliance must be daily habit, not "
            "a last-minute scramble.",
        ),
        _S(
            "Key Food Safety Risks",
            [
                "Biological hazards: Salmonella, E. coli, Listeria, and norovirus from "
                "contaminated food or handlers",
                "Chemical hazards: cleaning-agent residues, pesticide traces, unlabelled "
                "chemicals stored near food",
                "Physical hazards: glass shards, metal fragments, hair, or packaging pieces",
                "Cross-contamination: raw meat juices touching ready-to-eat foods or surfaces",
                "Time–temperature abuse: food left too long in the danger zone (5–60 °C)",
            ],
            "title-content",
            "Give one canteen example per hazard: undercooked chicken (biological), "
            "sanitiser sprayed near uncovered salad (chemical), a broken glass near the "
            "serving counter (physical). Ask staff for examples they have seen.",
        ),
        _S(
            "The Temperature Danger Zone",
            [
                "Bacteria multiply fastest between 5 °C and 60 °C (41–140 °F) — "
                "doubling every ~20 minutes",
                "Never leave perishable food in the danger zone for more than 2 hours "
                "(1 hour if ambient temperature exceeds 32 °C)",
            ],
            "title-content",
            "This is the single most important concept in the session. Draw the danger "
            "zone on a flip chart. Quiz the group: 'The fridge broke at 10 am — when "
            "must the milk be discarded?'",
            table={
                "headers": ["Stage", "Safe Temperature", "Rule"],
                "rows": [
                    ["Refrigeration", "≤ 5 °C (41 °F)", "Check twice daily with a calibrated thermometer"],
                    ["Danger zone", "5–60 °C (41–140 °F)", "Maximum 2 hours cumulative exposure"],
                    ["Hot holding", "≥ 60 °C (140 °F)", "Stir and check temperature hourly"],
                    ["Freezing", "≤ −18 °C (0 °F)", "Freeze fresh stock promptly; label dates"],
                ],
            },
        ),
        _S(
            "Personal Hygiene Checklist",
            [
                "Wash hands with soap for at least 20 seconds: before work, after toilet, "
                "after touching raw food, waste, or face",
                "Wear a clean uniform, apron, hairnet, and closed shoes every shift",
                "Keep nails short and clean; no nail polish or jewellery except a plain band",
                "Cover cuts and wounds with a waterproof blue bandage plus a glove",
                "Report illness — vomiting, diarrhoea, jaundice, infected skin — and stay "
                "off food-handling duty until cleared",
                "Use single-use gloves for ready-to-eat food; change them every 4 hours "
                "or when torn",
            ],
            "checklist",
            "Demonstrate the WHO 6-step handwashing technique live if a sink is nearby. "
            "Remind staff that gloves are not a substitute for handwashing.",
        ),
        _S(
            "Cleaning vs Sanitising",
            [
                "Cleaning removes visible dirt and grease with detergent and hot water",
                "Sanitising kills microbes on an already-clean surface — it cannot work "
                "through grease",
                "Always clean first, then sanitise; respect the contact time on the label",
                "Use the correct dilution — more chemical is not more effective and leaves "
                "toxic residues",
                "Colour-code cloths and mops: e.g., red for washrooms, green for food areas",
                "Clean as you go: wipe spills immediately, sanitise boards between tasks",
            ],
            "two-column",
            "Explain the two-step logic with a simple analogy: you cannot disinfect a "
            "dirty wound. Show the dilution chart posted in the chemical store.",
            columns=["Cleaning", "Sanitising"],
        ),
        _S(
            "Pest Control",
            [
                "Seal entry points: door sweeps, window screens, sealed pipe gaps",
                "Store all food 15 cm off the floor in sealed, labelled containers",
                "Remove waste daily; keep bins covered and the area around them clean",
                "Inspect insect traps and rodent stations weekly and log findings",
                "Never spray pesticides near food or food-contact surfaces yourself — "
                "call the licensed pest-control operator",
                "Report any sighting or droppings to the supervisor immediately",
            ],
            "two-column",
            "Pests carry Salmonella, E. coli, and allergens. One cockroach sighting by a "
            "patient's attendant can destroy trust in the whole hospital kitchen.",
            columns=["Prevention", "Monitoring & Action"],
        ),
        _S(
            "Receiving & Storage",
            [
                "Check delivery temperatures: chilled ≤ 5 °C, frozen ≤ −18 °C — reject "
                "anything warmer",
                "Reject damaged packaging, dented cans, expired items, or off-smell produce",
                "Apply FIFO (first in, first out) and FEFO (first expired, first out); "
                "label everything with dates",
                "Store raw meat on the lowest shelves, below cooked and ready-to-eat foods",
                "Keep dry stores cool, dry, ventilated, and 15 cm off the floor",
                "Record supplier name, item, quantity, and temperature on the receiving log",
            ],
            "title-content",
            "Walk the group through the actual receiving area after this slide if possible. "
            "Show where raw chicken is stored versus cooked rice — the separation must be "
            "visible.",
        ),
        _S(
            "Safe Food Preparation",
            [
                "Thaw frozen food in the refrigerator, under cold running water, or in the "
                "microwave — never on the countertop",
                "Use colour-coded boards and knives: red for raw meat, blue for raw fish, "
                "green for vegetables, white for cooked food",
                "Wash fruits and vegetables thoroughly under running potable water",
                "Marinate only in the refrigerator, never at room temperature",
                "Prepare raw and ready-to-eat foods at separate times or stations",
                "Limit preparation batches so food spends minimal time at room temperature",
            ],
            "title-content",
            "Ask: 'Where do you thaw chicken at home?' — then contrast home habits with "
            "canteen rules. Show the colour-coded boards the kitchen actually uses.",
        ),
        _S(
            "Safe Cooking Temperatures",
            [
                "Always verify with a calibrated food thermometer — colour is not reliable",
                "Insert the probe into the thickest part, away from bone",
                "Calibrate thermometers weekly in ice water (should read 0 °C)",
            ],
            "title-content",
            "Demonstrate with a real thermometer and a piece of chicken if the kitchen is "
            "accessible. Undercooking is the top cause of poultry-related outbreaks.",
            table={
                "headers": ["Food", "Minimum Internal Temperature"],
                "rows": [
                    ["Poultry (whole, pieces, ground)", "74 °C (165 °F)"],
                    ["Ground beef, pork, lamb", "71 °C (160 °F)"],
                    ["Fish and seafood", "63 °C (145 °F)"],
                    ["Pork chops, steaks, roasts", "63 °C (145 °F) + 3 min rest"],
                    ["Eggs for immediate service", "63 °C (145 °F)"],
                    ["Reheated / leftover foods", "74 °C (165 °F)"],
                ],
            },
        ),
        _S(
            "Cooling & Reheating",
            [
                "Cool cooked food fast: from 60 °C to 21 °C within 2 hours, then to 5 °C "
                "within 4 more hours",
                "Use shallow pans, ice baths, and stirring to speed cooling — never cool a "
                "deep pot on the counter",
                "Refrigerate cooled food promptly in covered, labelled containers",
                "Reheat only once, rapidly, to a steaming 74 °C (165 °F) throughout",
                "Discard food that stayed too long in the danger zone — when in doubt, "
                "throw it out",
            ],
            "title-content",
            "Bacillus cereus in cooled rice and Clostridium perfringens in cooling curries "
            "are classic hospital-kitchen outbreaks. The two-stage cooling rule prevents both.",
        ),
        _S(
            "Serving & Holding",
            [
                "Hold hot food at or above 60 °C and cold food at or below 5 °C — check hourly",
                "Never mix fresh batches into food already on display; use small replenishment "
                "trays",
                "Protect displayed food with sneeze guards and covers",
                "Provide separate serving utensils for each dish; never let hands touch "
                "ready-to-eat food",
                "Discard any food held in the danger zone beyond 2 hours — do not taste-test "
                "to decide",
            ],
            "title-content",
            "The serving counter is where patients and attendants judge your hygiene. "
            "A clean, guarded, well-labelled display builds confidence.",
        ),
        _S(
            "Allergen Management",
            [
                "The 9 major allergens: milk, eggs, fish, shellfish, tree nuts, peanuts, "
                "wheat, soy, and sesame",
                "Label menus and display cards clearly when dishes contain allergens",
                "Prepare allergen-free meals first, with cleaned equipment and utensils",
                "Never guess — check ingredient labels and ask the patient about allergies",
                "Train all serving staff on the emergency response for anaphylaxis",
            ],
            "comparison",
            "For hospital canteens serving patients, allergen control is clinical safety, "
            "not just preference. One undeclared peanut trace can trigger anaphylaxis.",
            columns=["The 9 Major Allergens", "Control Measures"],
        ),
        _S(
            "Water & Ice Safety",
            [
                "Use only potable water for cooking, drinking, washing produce, and making ice",
                "Clean and disinfect overhead/underground water tanks at least every 6 months",
                "If using RO/UV treatment, replace filters and service units on schedule",
                "Make ice from safe water and handle it with scoops — never with hands or glasses",
                "Test water quality periodically (microbiological + chemical) and keep reports",
            ],
            "title-content",
            "Contaminated water or ice can sicken hundreds at once. Show the latest water "
            "test report to prove the system works.",
        ),
        _S(
            "Waste Management",
            [
                "Segregate waste at source: food waste, recyclables, and general waste",
                "Use foot-operated, covered, leak-proof bins lined with bags",
                "Remove waste from food areas at least daily — more often in summer",
                "Clean and disinfect bins and the waste storage area after each emptying",
                "Keep waste storage away from food preparation and receiving areas",
                "Maintain grease traps; never pour oil down the drain",
            ],
            "title-content",
            "Overflowing bins are the fastest route to a pest infestation and a failed "
            "inspection. Assign clear ownership: who empties which bin, when.",
        ),
        _S(
            "HACCP: The 7 Principles",
            [
                "Conduct a hazard analysis for each menu item and process",
                "Determine the Critical Control Points (CCPs) — e.g., cooking, cooling",
                "Establish critical limits for each CCP (temperatures, times)",
                "Set up monitoring procedures for every CCP",
                "Define corrective actions when a limit is breached",
                "Verify the system works (calibration, audits, reviews)",
                "Keep records of everything — if it isn't written down, it didn't happen",
            ],
            "timeline",
            "Walk through one dish — e.g., chicken curry — and map its CCPs: receiving "
            "temperature, cooking to 74 °C, cooling within 6 hours, reheating to 74 °C. "
            "That makes HACCP concrete instead of abstract.",
        ),
        _S(
            "Daily Inspection Checklist",
            [
                "Complete every row before service; the supervisor signs off",
                "Any 'No' triggers an immediate corrective action — logged, not hidden",
            ],
            "title-content",
            "Print this as a laminated sheet for the kitchen wall. Inspections pass when "
            "the paperwork matches reality — never fabricate a log entry.",
            table={
                "headers": ["Area", "Check Point", "Frequency"],
                "rows": [
                    ["Personal hygiene", "Handwashing, uniforms, illness reporting", "Daily"],
                    ["Temperatures", "Fridge, freezer, and holding-unit logs", "Twice daily"],
                    ["Cleaning", "Sanitation schedule signed off", "Daily"],
                    ["Pest control", "Traps and stations inspected", "Weekly"],
                    ["Storage", "FIFO/FEFO, labelling, expiry dates", "Weekly"],
                    ["Water & waste", "Tank levels, bin emptying", "Daily"],
                ],
            },
        ),
        _S(
            "Documentation & Records",
            [
                "Temperature logs: deliveries, fridges, freezers, cooking, holding",
                "Cleaning and sanitation checklists, signed and dated",
                "Supplier records: invoices, certificates, receiving logs",
                "Staff training records: attendance, topics, assessments",
                "Corrective-action log: what went wrong, what was done, who verified",
                "Keep records for at least one year (or per local regulation)",
            ],
            "title-content",
            "Records are your proof during inspections and outbreak investigations. "
            "Show an example of a well-kept temperature log versus a blank one.",
        ),
        _S(
            "Staff Training",
            [
                "Induction training for every new handler before their first shift",
                "Annual refresher plus targeted sessions after any incident",
                "Hands-on demos: handwashing, thermometer use, allergen awareness",
                "Short toolbox talks (10 minutes) at shift start on rotating topics",
                "Assess understanding — a signature alone does not prove competence",
            ],
            "split-image-text",
            "Training is not a one-time event. Mention that untrained temporary staff "
            "during rush periods are a common weak link — brief them too.",
        ),
        _S(
            "Building a Food Safety Culture",
            [
                "Food safety is not a task on a checklist — it is a culture where every "
                "handler protects every patient.",
                "Leaders must model the behaviour: wash hands visibly, follow the rules, "
                "praise good practice.",
            ],
            "big-quote",
            "Pause here. Ask the group: 'What would you do if you saw a colleague skip "
            "handwashing during a rush?' Culture is what happens when nobody is watching.",
        ),
        _S(
            "Outbreak Response Plan",
            [
                "Stop service of the suspect food immediately and isolate/retain samples",
                "Notify the canteen manager, hospital infection-control team, and clinician",
                "Preserve evidence: keep samples refrigerated, secure all temperature logs",
                "Cooperate with the investigation; implement corrective actions and verify",
            ],
            "timeline",
            "Speed matters: the faster suspect food is isolated, the fewer people are "
            "exposed. Rehearse who calls whom — post the contact list in the kitchen.",
        ),
        _S(
            "Case Example: The Rice That Wasn't Cooled",
            [
                "A hospital canteen cooked a large batch of rice at noon and left it in a "
                "deep pot at room temperature until dinner service",
                "Bacillus cereus spores survived cooking and multiplied in the warm rice",
                "34 patients and staff developed vomiting within 6 hours of the meal",
                "Investigation found no cooling log and a 6-hour danger-zone exposure",
                "Lesson: cool rice fast in shallow trays, refrigerate within 2 hours, "
                "reheat once to steaming",
            ],
            "split-image-text",
            "This is a composite of real, well-documented outbreak patterns with cooked "
            "rice. Ask the group how their kitchen cools large batches today.",
        ),
        _S(
            "Common Violations to Avoid",
            [
                "✗ Bare-hand contact with ready-to-eat food",
                "✗ Cooked food held at room temperature 'until the rush'",
                "✗ Dirty wiping cloths used across raw and cooked areas",
                "✗ Pest sightings ignored or handled with unlabelled sprays",
                "✗ Expired or unlabelled ingredients kept 'just in case'",
                "✗ Temperature logs filled in from memory at shift end",
            ],
            "title-content",
            "Read each violation and ask for a show of hands: 'Seen this happen?' "
            "No blame — the goal is honest recognition, then fixing it.",
        ),
        _S(
            "Corrective Actions",
            [
                "Discard the affected batch and record the loss honestly",
                "Stop the line, clean and sanitise all contact surfaces",
                "Close the affected area and call the licensed pest operator",
                "Exclude the ill handler and review their recent tasks",
            ],
            "comparison",
            "Corrective action is not punishment — it is protection. Staff must feel safe "
            "reporting problems; hidden problems become outbreaks.",
            columns=["If This Happens", "Do This"],
        ),
        _S(
            "Preparing for an Audit",
            [
                "All records complete, signed, and filed for the required retention period",
                "Temperature logs current — no gaps, no back-filled entries",
                "Staff can explain their tasks: interview readiness beats memorised answers",
                "Premises walk-through: no clutter, labelled chemicals, intact screens",
                "Run a mock audit quarterly and close every finding with evidence",
            ],
            "checklist",
            "Auditors check three things: documents, premises, and people. If all three "
            "agree with each other, you pass.",
        ),
        _S(
            "Key Takeaways",
            [
                "Keep food out of the danger zone (5–60 °C): control time and temperature",
                "Separate raw from ready-to-eat — every time, no shortcuts",
                "Wash hands properly and report illness before handling food",
                "Clean first, then sanitise; document everything you do",
                "When in doubt, throw it out — patients trust us with their safety",
            ],
            "checklist",
            "Ask each participant to state one change they will make from tomorrow. "
            "End with: protecting patients starts in this kitchen.",
        ),
        _S(
            "References & Further Reading",
            [
                "World Health Organization — Five Keys to Safer Food (who.int/foodsafety)",
                "U.S. FDA Food Code — Chapters on temperature control and employee health",
                "ISO 22000:2018 — Food safety management systems requirements",
                "CDC — Foodborne illness surveillance and outbreak guidance (cdc.gov/foodsafety)",
                "Provincial food authority regulations and licensing requirements",
            ],
            "references",
            "Share these links with participants after the session for deeper reading.",
        ),
        _S(
            "Thank You",
            [],
            "thank-you",
            "Thank the participants for their attention and their daily work keeping "
            "patients safe. Open the floor for questions and discussion — the best "
            "learning often happens here.",
        ),
    ]


def build_sample_project() -> dict:
    """Build the complete 30-slide sample project (status 'ready')."""
    now = datetime.now().astimezone().isoformat()
    theme = get_theme("dark-green-gold")
    project = {
        "id": new_id("p_"),
        "title": _TITLE,
        "instructions": (
            "A 30-slide training deck for hospital canteen staff covering food safety "
            "hazards, temperature control, hygiene, HACCP, and incident response."
        ),
        "purpose": "Staff training workshop on food safety and hygiene",
        "audience": "Hospital canteen staff, food handlers, and supervisors",
        "knowledge_level": "Beginner to intermediate",
        "slide_count": 30,
        "theme": "dark-green-gold",
        "slide_size": "16:9",
        "provider": {"kind": "offline", "model": ""},
        "status": "ready",
        "outline": _outline(),
        "slides": [],
        "created": now,
        "updated": now,
    }
    # The final slide doubles as the Q&A prompt ("Questions & Discussion").
    project["slides"] = build_slides(project, project["outline"], theme)
    project["slide_count"] = len(project["slides"])
    return project
