#!/usr/bin/env python3
"""Writes 21 FICTIONAL example records: 18 short ones (one per persona in docs/claimant-journeys/personas.md) and 3 full ones (vehicle, contractor, estate money and authority).
Every name, number and event is invented.

  python3 seed.py OUTDIR      (python3 seed.py --help prints this and writes nothing)

writes OUTDIR/<id>.json plus OUTDIR/<id>-files/ (placeholder documents that show each exhibit's text; the placeholders carry fake author and
location metadata on purpose, so the scrubbing can be seen working). Then, for each record:

  python3 ../build_views.py OUTDIR/V1.json OUTDIR/V1-inward
  python3 ../build_home.py  OUTDIR/V1.json OUTDIR/V1-outward --files-dir OUTDIR/V1-files

Mix on purpose: documented, thin (account-only), disputed, time-uncertain, offer-on-table, counterparty gone. Each short record is clean under
--strict. Every exhibit says who wrote it. Nothing is shared or released unless the record says so, and these records say so on purpose."""
import json, os, shutil, subprocess, sys

UPD = "Oct 3, 2026, 9:00 AM CDT"
AUTHORS = {  # who wrote each exhibit, in order: c = claimant, o = other side, t = third party
    'V1': 'oto', 'V2': 'ooc', 'V3': 'oot', 'V4': 'ooc', 'V5': 'ooo', 'V6': 'ooo', 'S1': 'oco', 'S2': 'oco', 'S3': 'ooo', 'S4': 'otc', 'S5': 'ooo', 'S6': 'ooo',
    'I1': 'oto', 'I2': 'oto', 'I3': 'oto', 'I4': 'oto', 'I5': 'oot', 'I6': 'oto'}
FILE_EXT = {'Contract': '.pdf', 'Policy': '.pdf', 'Letter': '.pdf', 'Notice': '.pdf', 'Photo index': '.jpg'}
WHO = {'c': 'claimant', 'o': 'other_side', 't': 'third_party'}


def mk(id, title, product, summary, ask, amount, people, exhibits, facts, deadlines=None, **extra):
    meta = dict(title=title, product=product, summary=summary, ask=ask, amount=amount, jurisdiction="Example State (required input)",
                updated=UPD, footer="Fictional example.")
    meta.update(extra)
    issues = sorted({x for f in facts for x in f[6]})
    return id, dict(
        meta=meta,
        people=[dict(id=p[0], name=p[1], role=p[2]) for p in people],
        exhibits=[dict(id=e[0], title=e[1], date=e[2], kind=e[3], text=e[4], author=WHO[AUTHORS[id][i]], share=True, file=e[0] + FILE_EXT.get(e[3], '.png'))
                  for i, e in enumerate(exhibits)],
        facts=[dict(id=f[0], date=f[1], text=f[2], status=f[3], sources=[dict(ex=s[0], loc=s[1], quote=s[2], **({'later_document': True} if len(s) > 3 else {})) for s in f[4]],
                    people=f[5], issues=f[6], outward=True) for f in facts],
        issues=[dict(id=i, label=i.replace('-', ' ').capitalize()) for i in issues],
        deadlines=deadlines or [])


def d(label, source, date=None, wording=None, ex=None, by=None):
    out = dict(label=label, source=source, confirmed_by=by)
    for k, v in (('date', date), ('wording', wording), ('ex', ex)):
        if v:
            out[k] = v
    return out


B = [
 mk('V1', 'Used truck, "as is" sale, transmission failure', 'vehicle', "A used pickup bought 'as is' began slipping gears in the third week.", 'Refund or repair cost', '$4,800 (claimant-reported)',
    [('p1', 'Buyer', 'Claimant'), ('p2', 'Seller', 'Used-car dealer'), ('p3', 'Shop', 'Independent repair shop')],
    [('E1', 'Bill of sale', '2026-08-02', 'Contract', 'AS IS. NO WARRANTY. Price $9,400.'), ('E2', 'Shop estimate', '2026-08-24', 'Estimate', 'Transmission will not hold gear. Estimate to rebuild: $4,800.'), ('E3', 'Text from seller', '2026-08-25', 'Message', 'I told you it was as is.')],
    [('F1', '2026-08-02', 'Buyer paid $9,400; the bill of sale reads "AS IS. NO WARRANTY."', 'documented', [('E1', '', 'AS IS. NO WARRANTY.')], ['p1', 'p2'], ['sale-terms']),
     ('F2', '2026-08-20', 'The transmission began slipping about three weeks after purchase.', 'account', [], ['p1'], ['defect']),
     ('F3', '2026-08-24', 'A shop estimated $4,800 to rebuild the transmission.', 'documented', [('E2', '', 'Estimate to rebuild: $4,800.')], ['p3'], ['defect', 'cost']),
     ('F4', '2026-08-25', 'The seller texted that the truck was sold as is.', 'documented', [('E3', 'text message', 'I told you it was as is.')], ['p2'], ['sale-terms']),
     ('F5', '2026-07-30', 'The seller said in person that the truck had never had a problem.', 'disputed', [], ['p2'], ['statements'])],
    [d('Seller mentioned a time window', 'The claimant recalls the seller saying this in person; nothing in writing', wording='30-day window')]),
 mk('V2', 'New pickup, intermittent noise, many visits', 'vehicle', 'A retiree\'s new pickup makes an intermittent noise; the repair orders report no fault found.', 'Repair or a manufacturer review', 'Not entered',
    [('p1', 'Owner', 'Claimant'), ('p2', 'Daughter', 'Helps with records'), ('p3', 'Dealer', 'Service department')],
    [('E1', 'Repair order 1', '2026-02-10', 'Repair order', 'Customer states clunk over bumps. Technician: no fault found.'), ('E2', 'Repair order 4', '2026-07-19', 'Repair order', 'Customer states clunk over bumps. Could not duplicate.'), ('E3', 'Voice memo transcript', '2026-07-21', 'Recording', 'You can hear it right there on the left side.')],
    [('F1', '2026-02-10', 'First visit: the dealer wrote "no fault found" for a clunk over bumps.', 'documented', [('E1', '', 'no fault found')], ['p3'], ['noise']),
     ('F2', '2026-07-19', 'Fourth visit: the dealer wrote "Could not duplicate."', 'documented', [('E2', '', 'Could not duplicate.')], ['p3'], ['noise']),
     ('F3', '2026-07-21', 'The owner recorded a voice memo while the noise occurred.', 'documented', [('E3', 'transcript', 'You can hear it right there on the left side.')], ['p1'], ['noise']),
     ('F4', '2026-05-01', 'Visits two and three are described by the owner; the paper copies are not yet found.', 'account', [], ['p1', 'p2'], ['records'])],
    [d('Warranty paperwork mentions an arbitration program', 'Page 14 of the warranty booklet, as the owner reads it', date='2026-12-31')]),
 mk('V3', 'Leased car used for gig driving', 'vehicle', 'A leased car used for gig driving has repeat brake warnings; the owner loses income when it is in the shop.', 'Resolution and lost income', '$3,200 lost earnings (claimant-reported)',
    [('p1', 'Driver', 'Claimant'), ('p2', 'Lessor', 'Leasing company'), ('p3', 'Dealer', 'Service department')],
    [('E1', 'Lease agreement', '2026-01-15', 'Contract', 'Lessee is responsible for maintenance and repairs outside warranty.'), ('E2', 'Repair order', '2026-06-02', 'Repair order', 'Brake warning light on. Replaced sensor.'), ('E3', 'Earnings export', '2026-06-30', 'Spreadsheet', 'Week of June 1: $0. Week of June 8: $410.')],
    [('F1', '2026-01-15', 'The lease agreement makes the lessee responsible for repairs outside warranty.', 'documented', [('E1', '', 'outside warranty')], ['p1', 'p2'], ['lease-terms']),
     ('F2', '2026-06-02', 'The dealer replaced a sensor for a brake warning light.', 'documented', [('E2', '', 'Replaced sensor.')], ['p3'], ['defect']),
     ('F3', '2026-06-08', 'Earnings were $0 the week of June 1.', 'documented', [('E3', '', 'Week of June 1: $0.', True)], ['p1'], ['income-loss']),
     ('F4', '2026-06-15', 'The warning light returned a week after the repair.', 'account', [], ['p1'], ['defect'])]),
 mk('V4', 'Motorhome with defects in the living area', 'vehicle', 'A motorhome has water leaks and a failed slide-out; two warranties apply (chassis and coach).', 'Repair or buy-back', '$12,000 estimated repairs (claimant-reported)',
    [('p1', 'Owner', 'Claimant'), ('p2', 'Coach maker', 'Manufacturer of the living area'), ('p3', 'Chassis maker', 'Manufacturer of the vehicle base')],
    [('E1', 'Coach warranty', '2025-05-01', 'Warranty', 'Limited warranty on the living area: 12 months.'), ('E2', 'Service invoice', '2026-03-12', 'Invoice', 'Slide-out motor replaced. Water intrusion noted at roof seam.'), ('E3', 'Photos log', '2026-03-14', 'Photo index', 'Ceiling stain, bedroom, left of vent.')],
    [('F1', '2025-05-01', 'The coach warranty covers the living area for 12 months.', 'documented', [('E1', '', 'Limited warranty on the living area: 12 months.')], ['p2'], ['warranty']),
     ('F2', '2026-03-12', 'A dealer replaced the slide-out motor and noted water intrusion at the roof seam.', 'documented', [('E2', '', 'Water intrusion noted at roof seam.')], ['p2'], ['defect']),
     ('F3', '2026-03-14', 'The owner photographed a ceiling stain.', 'documented', [('E3', '', 'Ceiling stain, bedroom, left of vent.')], ['p1'], ['defect']),
     ('F4', '2026-04-02', 'The owner reports the chassis maker said the leak is the coach maker\'s responsibility.', 'account', [], ['p1', 'p3'], ['warranty'])],
    [d('Coach warranty period', 'Coach warranty, first page', wording='12 months', ex='E1')]),
 mk('V5', 'Motorcycle safety defect, dealer changed hands', 'vehicle', 'A motorcycle has a recurring front-brake fault; the selling dealer has closed.', 'Repair or refund', 'Not entered',
    [('p1', 'Rider', 'Claimant'), ('p2', 'Former dealer', 'Closed business'), ('p3', 'Manufacturer', 'Maker')],
    [('E1', 'Purchase invoice', '2025-09-10', 'Invoice', 'Front brake assembly. New motorcycle.'), ('E2', 'Recall notice', '2026-02-05', 'Notice', 'Front brake hose may leak under heavy braking.'), ('E3', 'Email from manufacturer', '2026-05-20', 'Email', 'We cannot locate a dealer to complete this recall.')],
    [('F1', '2025-09-10', 'The rider bought a new motorcycle.', 'documented', [('E1', '', 'New motorcycle.')], ['p1', 'p2'], ['sale']),
     ('F2', '2026-02-05', 'The manufacturer issued a recall notice for the front brake hose.', 'documented', [('E2', '', 'Front brake hose may leak under heavy braking.')], ['p3'], ['recall']),
     ('F3', '2026-05-20', 'The manufacturer emailed that it could not locate a dealer to complete the recall.', 'documented', [('E3', '', 'We cannot locate a dealer to complete this recall.')], ['p3'], ['recall']),
     ('F4', '2026-04-10', 'The rider reports a brake fault on a downhill road.', 'account', [], ['p1'], ['defect'])]),
 mk('V6', 'Electric car, repeated electrical faults, open recalls', 'vehicle', 'An electric car has had repeat visits for display and charging faults, with open recalls.', 'Manufacturer review', '$41,000 vehicle price (claimant-reported)',
    [('p1', 'Owner', 'Claimant'), ('p2', 'Dealer', 'Service department'), ('p3', 'Manufacturer', 'Customer care')],
    [('E1', 'Repair order 12', '2026-03-03', 'Repair order', 'Display goes black while driving. Updated software per recall.'), ('E2', 'Repair order 19', '2026-07-08', 'Repair order', 'Charge port stuck. Replaced charge port.'), ('E3', 'Customer care email', '2026-08-01', 'Email', 'Your case is under review.')],
    [('F1', '2026-03-03', 'The dealer updated software per recall for a display that goes black while driving.', 'documented', [('E1', '', 'Display goes black while driving.')], ['p2'], ['display']),
     ('F2', '2026-07-08', 'The dealer replaced the charge port.', 'documented', [('E2', '', 'Replaced charge port.')], ['p2'], ['charging']),
     ('F3', '2026-08-01', 'Customer care wrote that the case is under review.', 'documented', [('E3', '', 'Your case is under review.')], ['p3'], ['review']),
     ('F4', '2026-08-15', 'The charge handle stuck again at a public charger.', 'account', [], ['p1'], ['charging'])]),
 mk('S1', 'Home repair deposit, work never started', 'contractor', 'A homeowner paid a deposit for a repair; work has not started and messages have grown vague.', 'Refund of deposit', '$8,000 (claimant-reported)',
    [('p1', 'Homeowner', 'Claimant'), ('p2', 'Contractor', 'Business owner')],
    [('E1', 'Signed estimate', '2026-04-02', 'Contract', 'Deposit of $8,000 required to begin.'), ('E2', 'Cancelled check', '2026-04-05', 'Payment', 'Pay to the order of Contractor. $8,000.'), ('E3', 'Text thread', '2026-07-20', 'Messages', 'Contractor: Should start soon.')],
    [('F1', '2026-04-02', 'The signed estimate says a deposit of $8,000 is required to begin.', 'documented', [('E1', '', 'Deposit of $8,000 required to begin.')], ['p1', 'p2'], ['agreement']),
     ('F2', '2026-04-05', 'The homeowner paid $8,000 by check.', 'documented', [('E2', '', '$8,000.')], ['p1'], ['payment']),
     ('F3', '2026-07-20', 'The contractor texted "Should start soon."', 'documented', [('E3', '', 'Should start soon.')], ['p2'], ['delay']),
     ('F4', '2026-09-01', 'No work has been done at the property.', 'account', [], ['p1'], ['delay'])]),
 mk('S2', 'Rental security deposit withheld', 'contractor', 'A renter moved out; the landlord kept the full deposit citing damages.', 'Return of deposit', '$1,850 (claimant-reported)',
    [('p1', 'Renter', 'Claimant'), ('p2', 'Landlord', 'Property owner')],
    [('E1', 'Lease', '2025-08-01', 'Contract', 'Security deposit: $1,850.'), ('E2', 'Move-in photos', '2025-08-01', 'Photo index', '14 photos taken at move-in, including carpet in living room.'), ('E3', 'Landlord letter', '2026-09-20', 'Letter', 'Deposit retained for carpet replacement and cleaning.')],
    [('F1', '2025-08-01', 'The lease states a security deposit of $1,850.', 'documented', [('E1', '', 'Security deposit: $1,850.')], ['p1', 'p2'], ['deposit']),
     ('F2', '2025-08-01', 'The renter took 14 photos at move-in, including the living-room carpet.', 'documented', [('E2', '', '14 photos taken at move-in')], ['p1'], ['condition']),
     ('F3', '2026-09-20', 'The landlord wrote that the deposit was retained for carpet replacement and cleaning.', 'documented', [('E3', '', 'Deposit retained for carpet replacement and cleaning.')], ['p2'], ['deposit']),
     ('F4', '2026-08-31', 'The renter reports leaving the unit clean and returning the keys on August 31.', 'account', [], ['p1'], ['condition'])],
    [],
    offers='none reported'),
 mk('S3', 'Car repair bill doubled', 'contractor', 'A repair shop raised the bill after finding something else and held the car until paid.', 'Refund of the difference', '$1,100 (claimant-reported)',
    [('p1', 'Customer', 'Claimant'), ('p2', 'Shop', 'Repair shop')],
    [('E1', 'Written estimate', '2026-05-10', 'Estimate', 'Replace water pump. Estimate $780.'), ('E2', 'Final invoice', '2026-05-14', 'Invoice', 'Water pump and belt set. Total $1,880.'), ('E3', 'Payment receipt', '2026-05-14', 'Receipt', 'Paid in full, car released.')],
    [('F1', '2026-05-10', 'The written estimate was $780 to replace a water pump.', 'documented', [('E1', '', 'Estimate $780.')], ['p2'], ['estimate']),
     ('F2', '2026-05-14', 'The final invoice was $1,880 for the pump and a belt set.', 'documented', [('E2', '', 'Total $1,880.')], ['p2'], ['bill']),
     ('F3', '2026-05-14', 'The customer paid in full and the car was released.', 'documented', [('E3', '', 'Paid in full, car released.')], ['p1'], ['payment']),
     ('F4', '2026-05-13', 'The customer reports a phone call approving the belt, not the full amount.', 'disputed', [], ['p1', 'p2'], ['estimate'])],
    offers='Shop offered a $200 credit (claimant reported)'),
 mk('S4', 'Wedding vendor vanished', 'contractor', 'A photographer stopped replying five weeks before the wedding.', 'Refund of deposit or a replacement', '$2,400 (claimant-reported)',
    [('p1', 'Couple', 'Claimants'), ('p2', 'Vendor', 'Photographer')],
    [('E1', 'Booking contract', '2026-01-10', 'Contract', 'Retainer of $2,400 is non-refundable except as stated.'), ('E2', 'Card statement', '2026-01-11', 'Statement', 'Photo studio $2,400. Disputes must be made within 60 days of the statement date.'), ('E3', 'Email thread', '2026-08-02', 'Email', 'Couple: Please confirm you are still booked for September 6.')],
    [('F1', '2026-01-10', 'The contract states a retainer of $2,400, "non-refundable except as stated."', 'documented', [('E1', '', 'non-refundable except as stated')], ['p1', 'p2'], ['agreement']),
     ('F2', '2026-01-11', 'The retainer appears on a card statement.', 'documented', [('E2', '', 'Photo studio $2,400.')], ['p1'], ['payment']),
     ('F3', '2026-08-02', 'The couple emailed asking the vendor to confirm the September 6 booking.', 'documented', [('E3', '', 'Please confirm you are still booked for September 6.')], ['p1'], ['contact']),
     ('F4', '2026-08-20', 'The vendor has not replied to emails or calls since July.', 'account', [], ['p1'], ['contact'])],
    [d('Card dispute window', "Card issuer's statement, as the claimant reads it", wording='within 60 days of the statement date', ex='E2')]),
 mk('S5', 'Moving company holding belongings', 'contractor', 'A moving company is holding a senior\'s belongings until an additional payment is made.', 'Delivery of belongings', 'Additional demand of $2,900 (claimant-reported)',
    [('p1', 'Customer', 'Claimant'), ('p2', 'Daughter', 'Helps'), ('p3', 'Mover', 'Moving company')],
    [('E1', 'Moving estimate', '2026-08-01', 'Estimate', 'Estimate for 2 bedrooms: $2,100.'), ('E2', 'Text messages', '2026-08-20', 'Messages', 'Mover: Pay the extra $2,900 or the truck does not unload.'), ('E3', 'Bill of lading', '2026-08-19', 'Contract', 'Shipment: household goods, 2 bedrooms.')],
    [('F1', '2026-08-01', 'The estimate was $2,100 for two bedrooms.', 'documented', [('E1', '', 'Estimate for 2 bedrooms: $2,100.')], ['p3'], ['estimate']),
     ('F2', '2026-08-19', 'The bill of lading describes household goods, 2 bedrooms.', 'documented', [('E3', '', 'household goods, 2 bedrooms')], ['p3'], ['agreement']),
     ('F3', '2026-08-20', 'The mover texted that the truck would not unload unless an extra $2,900 was paid.', 'documented', [('E2', '', 'Pay the extra $2,900 or the truck does not unload.')], ['p3'], ['demand']),
     ('F4', '2026-08-21', 'The customer reports the belongings are still on the truck.', 'account', [], ['p1', 'p2'], ['possession'])]),
 mk('S6', 'Tuition paid to a program that closed', 'contractor', 'A student paid tuition for a training program that closed mid-term.', 'Refund of tuition', '$6,500 (claimant-reported)',
    [('p1', 'Student', 'Claimant'), ('p2', 'School', 'Training program')],
    [('E1', 'Enrollment agreement', '2026-01-05', 'Contract', 'Tuition: $6,500 per term.'), ('E2', 'Closure notice', '2026-04-12', 'Notice', 'The program will close effective April 30.'), ('E3', 'Receipt', '2026-01-05', 'Receipt', 'Tuition payment $6,500.')],
    [('F1', '2026-01-05', 'The enrollment agreement lists tuition of $6,500 per term.', 'documented', [('E1', '', 'Tuition: $6,500 per term.')], ['p1', 'p2'], ['agreement']),
     ('F2', '2026-01-05', 'The student paid $6,500.', 'documented', [('E3', '', 'Tuition payment $6,500.')], ['p1'], ['payment']),
     ('F3', '2026-04-12', 'The school announced it would close effective April 30.', 'documented', [('E2', '', 'The program will close effective April 30.')], ['p2'], ['closure']),
     ('F4', '2026-05-15', 'The student reports other students received no refunds.', 'account', [], ['p1'], ['closure'])]),
 mk('I1', 'Employer plan denies a treatment', 'insurance', 'An employer-plan member was denied a specialist treatment as "not medically necessary."', 'Coverage of the treatment', '$18,000 estimated cost (claimant-reported)',
    [('p1', 'Member', 'Claimant'), ('p2', 'Plan', 'Health plan'), ('p3', 'Doctor', 'Treating specialist')],
    [('E1', 'Denial letter', '2026-09-10', 'Letter', 'We denied this treatment because it is not medically necessary. You may appeal within 180 days of this letter.'), ('E2', 'Doctor letter', '2026-09-18', 'Letter', 'This treatment is the standard of care for her condition.'), ('E3', 'Plan document excerpt', '2026-01-01', 'Policy', 'Medically necessary means services that a physician would provide in accordance with generally accepted standards.')],
    [('F1', '2026-09-10', 'The plan\'s letter denied the treatment as "not medically necessary."', 'documented', [('E1', '', 'not medically necessary')], ['p2'], ['denial']),
     ('F2', '2026-09-10', 'The letter says an appeal may be made within 180 days of the letter.', 'documented', [('E1', '', 'within 180 days of this letter')], ['p2'], ['appeal']),
     ('F3', '2026-09-18', 'The treating doctor wrote that the treatment is the standard of care.', 'documented', [('E2', '', 'standard of care')], ['p3'], ['medical']),
     ('F4', '2026-01-01', 'The plan document defines "medically necessary."', 'documented', [('E3', '', 'generally accepted standards')], ['p2'], ['policy'])],
    [d('Appeal', 'The denial letter, third sentence', wording='within 180 days of this letter', ex='E1')]),
 mk('I2', 'Hail-damaged roof, partial payment', 'insurance', 'A homeowner\'s insurer paid part of a roof claim; the contractor\'s estimate is higher.', 'Additional payment', '$7,300 difference (claimant-reported)',
    [('p1', 'Homeowner', 'Claimant'), ('p2', 'Insurer', 'Home insurer'), ('p3', 'Contractor', 'Roofer')],
    [('E1', 'Insurer estimate', '2026-06-20', 'Estimate', 'Roof replacement, depreciated value: $9,100.'), ('E2', 'Contractor estimate', '2026-06-25', 'Estimate', 'Full roof replacement: $16,400.'), ('E3', 'Payment letter', '2026-06-28', 'Letter', 'Payment issued: $9,100.')],
    [('F1', '2026-06-20', 'The insurer\'s estimate was $9,100 for roof replacement at depreciated value.', 'documented', [('E1', '', '$9,100')], ['p2'], ['estimate']),
     ('F2', '2026-06-25', 'The contractor estimated $16,400 for full replacement.', 'documented', [('E2', '', '$16,400')], ['p3'], ['estimate']),
     ('F3', '2026-06-28', 'The insurer issued a payment of $9,100.', 'documented', [('E3', '', 'Payment issued: $9,100.')], ['p2'], ['payment']),
     ('F4', '2026-07-02', 'The homeowner reports hail damage on every slope.', 'account', [], ['p1'], ['damage'])]),
 mk('I3', 'Total-loss offer below replacement cost', 'insurance', 'An auto insurer declared a car a total loss and offered less than comparable vehicles cost.', 'A higher valuation', '$3,900 gap (claimant-reported)',
    [('p1', 'Driver', 'Claimant'), ('p2', 'Insurer', 'Auto insurer')],
    [('E1', 'Valuation report', '2026-08-04', 'Report', 'Actual cash value: $14,200.'), ('E2', 'Listings printout', '2026-08-06', 'Printout', 'Three comparable vehicles listed at $17,900, $18,300 and $18,000.'), ('E3', 'Rental notice', '2026-08-07', 'Notice', 'Rental coverage ends August 20.')],
    [('F1', '2026-08-04', 'The valuation report gave an actual cash value of $14,200.', 'documented', [('E1', '', '$14,200')], ['p2'], ['valuation']),
     ('F2', '2026-08-06', 'The driver found three comparable listings at $17,900, $18,300 and $18,000.', 'documented', [('E2', '', '$17,900, $18,300 and $18,000')], ['p1'], ['valuation']),
     ('F3', '2026-08-07', 'The insurer wrote that rental coverage ends August 20.', 'documented', [('E3', '', 'Rental coverage ends August 20.')], ['p2'], ['rental']),
     ('F4', '2026-08-08', 'The driver reports the listings are in the same area.', 'account', [], ['p1'], ['valuation'])],
    [d('Rental coverage ends', 'Insurer notice dated August 7', date='2026-08-20', wording='Rental coverage ends August 20.', ex='E3')]),
 mk('I4', 'Disability benefit terminated', 'insurance', 'A long-term disability benefit was terminated after a records review; the claimant is ill and fatigued.', 'Reinstatement', 'Monthly benefit $2,100 (claimant-reported)',
    [('p1', 'Claimant', 'Benefit recipient'), ('p2', 'Plan', 'Disability insurer'), ('p3', 'Partner', 'Helps with paperwork')],
    [('E1', 'Termination letter', '2026-09-02', 'Letter', 'Your benefit ends September 30. You may request review within 180 days.'), ('E2', 'Physician statement', '2026-09-15', 'Letter', 'Patient remains unable to sustain full-time work.'), ('E3', 'Plan summary', '2025-01-01', 'Policy', 'Disability means unable to perform the material duties of any occupation.')],
    [('F1', '2026-09-02', 'The insurer wrote that the benefit ends September 30.', 'documented', [('E1', '', 'Your benefit ends September 30.')], ['p2'], ['termination']),
     ('F2', '2026-09-02', 'The letter says a review may be requested within 180 days.', 'documented', [('E1', '', 'within 180 days')], ['p2'], ['appeal']),
     ('F3', '2026-09-15', 'A physician wrote the patient remains unable to sustain full-time work.', 'documented', [('E2', '', 'unable to sustain full-time work')], ['p1'], ['medical']),
     ('F4', '2026-09-20', 'The claimant reports the insurer\'s surveillance covered only one afternoon.', 'account', [], ['p1', 'p3'], ['termination'])],
    [d('Review request', 'Termination letter; the claimant believes shorter windows may apply under the plan', wording='within 180 days', ex='E1')]),
 mk('I5', 'Travel insurance refund refused', 'insurance', 'A trip was cancelled for a family illness; the travel insurer refused a refund citing an exclusion.', 'Refund of trip cost', '$2,700 (claimant-reported)',
    [('p1', 'Traveler', 'Claimant'), ('p2', 'Insurer', 'Travel insurer')],
    [('E1', 'Policy', '2026-03-01', 'Policy', 'Covered reasons include illness of an immediate family member.'), ('E2', 'Denial email', '2026-07-12', 'Email', 'Claim denied: pre-existing condition exclusion applies.'), ('E3', 'Hospital letter', '2026-06-25', 'Letter', 'Admitted June 24 with an acute episode.')],
    [('F1', '2026-03-01', 'The policy lists illness of an immediate family member as a covered reason.', 'documented', [('E1', '', 'illness of an immediate family member')], ['p2'], ['policy']),
     ('F2', '2026-06-25', 'A hospital letter states the family member was admitted June 24.', 'documented', [('E3', '', 'Admitted June 24')], ['p1'], ['medical']),
     ('F3', '2026-07-12', 'The insurer denied the claim citing a pre-existing condition exclusion.', 'documented', [('E2', '', 'pre-existing condition exclusion applies')], ['p2'], ['denial']),
     ('F4', '2026-07-01', 'The traveler reports the family member had no prior hospital stays.', 'account', [], ['p1'], ['medical'])],
    offers='none reported'),
 mk('I6', 'Out-of-network surprise bill', 'insurance', 'A patient received a bill for an out-of-network provider at an in-network hospital.', 'Reprocessing at the in-network rate', '$5,600 (claimant-reported)',
    [('p1', 'Patient', 'Claimant'), ('p2', 'Plan', 'Health plan'), ('p3', 'Provider', 'Billing provider')],
    [('E1', 'Explanation of benefits', '2026-08-10', 'Statement', 'Out-of-network provider. Patient responsibility: $5,600.'), ('E2', 'Hospital admission form', '2026-07-30', 'Form', 'Facility: in network.'), ('E3', 'Provider bill', '2026-08-18', 'Bill', 'Balance due $5,600.')],
    [('F1', '2026-07-30', 'The admission form lists the facility as in network.', 'documented', [('E2', '', 'Facility: in network.')], ['p1'], ['network']),
     ('F2', '2026-08-10', 'The explanation of benefits shows an out-of-network provider and $5,600 patient responsibility.', 'documented', [('E1', '', 'Patient responsibility: $5,600.')], ['p2'], ['bill']),
     ('F3', '2026-08-18', 'The provider billed a balance of $5,600.', 'documented', [('E3', '', 'Balance due $5,600.')], ['p3'], ['bill']),
     ('F4', '2026-07-30', 'The patient reports not choosing the provider.', 'account', [], ['p1'], ['network'])]),
]

def X(id, title, date, kind, author, text, **kw):
    return dict(id=id, title=title, date=date, kind=kind, author=WHO[author], text=text, **kw)


def F(id, date, text, status, sources=(), people=(), issues=(), **kw):
    return dict(id=id, date=date, text=text, status=status, sources=[dict(ex=x) if isinstance(x, str) else x for x in sources], people=list(people), issues=list(issues), **kw)


# A full vehicle record: every field the tools read, including the ones that make the outward page careful.
FULL1 = dict(
    meta=dict(title='Electric car, a display that goes black (fictional full example)', product='vehicle', subtitle='Repair visits, a letter and a reply',
              summary=('An electric car\'s display goes black while driving. The dealer wrote “unable to duplicate” at the first visit and replaced the display unit at the second; '
                       'the manufacturer wrote that the case is “under review.” This page holds {count:facts} dated entries and {count:documents} documents.'),
              ask='A manufacturer review of the display failures', amount='Not entered', jurisdiction='Example State (required input)', lawyer='none reported',
              sent_to_other_side='A letter to the manufacturer on October 2, 2025', offers='none reported', absences='Any document that shows the display unit was tested before it was replaced',
              contact_note='Questions: reply to the person who sent you this page.', footer='Fictional example. Every name and number is invented.', claimant_label="the owner's",
              updated=UPD, asof='2025-11-05', review_opened='2025-10-20',
              share_gate=dict(recipient='Example Manufacturer, customer care (fictional)', confidentiality_checked=True, names_checked=True, defamation_reminder_ack=True, attorney_read=True),
              banned=['lemon'], held_phrases=['considering a letter to the state agency']),
    people=[dict(id='p1', name='Owner', role='Claimant'), dict(id='p2', name='Dealer', role='Service department'), dict(id='p3', name='Manufacturer', role='Customer care')],
    issues=[dict(id='display', label='Display'), dict(id='contact', label='Contact with the manufacturer'), dict(id='purchase', label='Purchase')],
    lanes=[dict(id='paper', label='Purchase and paperwork'), dict(id='dealer', label='Dealer visits'), dict(id='contacts', label='Contact with the manufacturer'), dict(id='media', label='Photos and recordings')],
    exhibits=[
        X('E1', 'Purchase agreement', '2025-02-10', 'Contract', 'o', 'Delivered with 12 miles on the odometer. Limited warranty: within 36 months or 36,000 miles, whichever comes first.', share=True, file='E1.pdf'),
        X('E2', 'Repair order 1', '2025-04-14', 'Repair order', 'o', 'Customer states: display goes black. Technician: unable to duplicate. Software updated.', share=True, file='E2.png'),
        X('E3', 'Repair order 2', '2025-09-09', 'Repair order', 'o', 'Customer states: display goes black while driving. Replaced display unit. Odometer in: 4,120. Odometer out: 4,131.', share=True, file='E3.png'),
        X('E4', "Owner's letter to the manufacturer", '2025-10-02', 'Letter', 'c', 'We ask the manufacturer to review the repeated display failures. We last drove the car on October 1.', share=True, file='E4.pdf'),
        X('E5', 'Customer care reply', '2025-10-20', 'Email', 'o', 'Thank you for contacting us. Your case is under review. We will follow up within 30 days.', share=True, file='E5.html'),
        X('E6', 'Message export (full)', '2025-04-01', 'Messages', 'c', 'Full export of the owner\'s messages with the dealer, April to October.', end='2025-10-20', share=False, file='E6.txt'),
        X('E7', 'Photos of the display', '2025-09-08', 'Photo index', 'c', 'Three photos of the black display, taken on the dashboard.', share=True, file='E7.jpg', feature=True, thumb='thumbs/E7.jpg',
          caption='Photos of the display, September 8, 2025'),
        X('E8', 'Recording of the display going black', '2025-09-08', 'Video', 'c', 'Recording from the passenger seat. The display goes black at the 20 second mark.', share=True, file='E8.mp4', feature=True,
          thumb='thumbs/E8.jpg', caption='Recording of the display going black while driving'),
        X('E9', 'Excerpt: the display goes black', '2025-09-08', 'Video excerpt', 'c', 'The display goes black.', excerpt_of='E8', share=True, file='E9.png'),
        X('E10', 'Dealer note about the visit', '2025-09-10', 'Note', 'o', 'Dealer note, internal.', share=False, needs_clearance='Counsel', file='E10.png'),
        X('E11', 'Second copy of repair order 2', '2025-09-09', 'Repair order', 'o', 'Customer states: display goes black while driving. Replaced display unit.', fold_into='E3', share=False, file='E11.png')],
    facts=[
        F('F1', '2025-02-10', 'The owner bought the car; the agreement lists delivery with “12 miles on the odometer.”', 'documented', ['E1'], ['p1', 'p2'], ['purchase'], lane='paper', outward=True),
        F('F2', '2025-04-14', 'First visit: the dealer wrote “unable to duplicate” for a display that goes black.', 'documented', ['E2'], ['p2'], ['display'], lane='dealer', outward=True),
        F('F3', '2025-09-09', 'Second visit: the dealer replaced the display unit.', 'documented', [dict(ex='E3', quote='Replaced display unit.')], ['p2'], ['display'], lane='dealer', outward=True),
        F('F4', '2025-09', 'The owner reports the display went black several times that month.', 'account', [], ['p1'], ['display'], date_precision='month', lane='dealer', outward=True),
        F('F5', '2025-10-02', 'The owner wrote to the manufacturer asking for a review of the display failures.', 'documented', ['E4'], ['p1', 'p3'], ['contact'], lane='contacts', outward=True),
        F('F6', '2025-10-20', 'The manufacturer wrote that the case is “under review.”', 'documented', ['E5'], ['p3'], ['contact'], lane='contacts', outward=True),
        F('F7', '2025-10-20', 'The manufacturer wrote that it will follow up “within 30 days.”', 'documented', ['E5'], ['p3'], ['contact'], lane='contacts', outward=True),
        F('F8', '2025-09-08', 'The owner recorded the display going black while driving.', 'documented', ['E8'], ['p1'], ['display'], lane='media', outward=True, grade='A', reviewed_by='owner'),
        F('F9', '2025-09-08', 'Excerpt of the recording: the display goes black.', 'documented', ['E9'], ['p1'], ['display'], lane='media', outward=True, excerpt_of='F8'),
        F('F10', '2025-10-05', 'The owner and the dealer give different accounts of whether the display was black at pick-up.', 'disputed', ['E6'], ['p1', 'p2'], ['display'], lane='dealer', outward=True),
        F('F11', '2025-10-06', 'Whether the display unit replaced on September 9 was the cause is not known.', 'open', [], ['p2'], ['display'], lane='dealer', outward=True),
        F('F12', '2025-09-10', 'A dealer note about the visit exists.', 'documented', ['E10'], ['p2'], ['display'], lane='dealer', outward=True),
        F('F13', '2025-10-21', 'The owner is considering a letter to the state agency.', 'account', [], ['p1'], ['contact'], lane='contacts', outward=False),
        F('F14', '2025-09-09', 'Second copy of the repair order for the second visit; it says the display unit was replaced.', 'documented', ['E11'], ['p2'], ['display'], lane='dealer', outward=True, fold_into='F3'),
        F('F15', '2025-11-01', 'The owner has not received the follow-up.', 'account', [], ['p1'], ['contact'], lane='contacts')],
    intervals=[dict(id='visits', label='Between the first and second visits', a='F2', b='F3'), dict(id='reply', label='Between the second visit and the manufacturer\'s reply', a='F3', b='F6')],
    spans=[dict(label='Review period after the reply', start='2025-10-20', end='2025-11-19', note='Computed from the two dates.', lanes=['contacts']),
           dict(label='Between the visits', start='2025-04-14', end='2025-09-09', lanes='all')],
    beats=[dict(title='Purchase and the first visit', line='The agreement and the first repair order.', **{'from': '2025-02-01', 'to': '2025-04-30'},
                prose=['The first repair order is dated {days:F1:F2} days after the purchase agreement.']),
           dict(title='The second visit', line='The display unit was replaced.', **{'from': '2025-09-01', 'to': '2025-09-30'},
                prose=['The second repair order lists two odometer readings, {miles:E3:4,120:4,131} miles apart.']),
           dict(title='The letter and the reply', line='The owner wrote; the manufacturer answered.', **{'from': '2025-10-01', 'to': '2025-10-31'},
                prose=['The reply is dated {days:F5:F6} days after the letter.'])],
    deadlines=[dict(label='Manufacturer follow-up', source='Customer care email of Oct 20, 2025', wording='within 30 days', ex='E5'),
               dict(label='Warranty claim period', source='Purchase agreement', wording='within 36 months or 36,000 miles', ex='E1', confirmed_by='Example Attorney')],
    held_back=[dict(phrase='internal call notes', why='Held until counsel has read them.')])

# A contractor record with counsel involved: the lawyer is counsel, not a party; a memo for counsel stays unshared; the share gate is not finished, so the outward page is a DRAFT.
FULL2 = dict(
    meta=dict(title='Roof-panel deposit, work never started (fictional full example)', product='contractor', subtitle='A quote, a check, and what was said since',
              summary='A deposit was paid against a quote. {count:documents} documents are shared on the outward page, listed below with what each shows.',
              ask='Return of the deposit', amount='$33,000 (claimant-reported)', jurisdiction='Example State (required input)',
              lawyer='Example Attorney, acting as a favor. The clients are the two owners; the attorney is not a party.', sent_to_other_side='A written refund request on September 1, 2026',
              offers='none reported', absences='Any document showing work at the property', contact_note='Questions: reply to the person who sent you this page.',
              footer='Fictional example. Every name and number is invented.', updated=UPD, asof='2026-10-03',
              share_gate=dict(recipient='Example Contractor and its lawyer (fictional)'), held_phrases=['preservation demand']),
    people=[dict(id='p1', name='Owner One', role='Claimant and client'), dict(id='p2', name='Owner Two', role='Claimant and client'), dict(id='p3', name='Contractor', role='Business'),
            dict(id='p4', name='Counsel', role='Attorney acting as a favor; not a party')],
    issues=[dict(id='payment', label='Payment'), dict(id='work', label='Work'), dict(id='communications', label='Communications')],
    exhibits=[
        X('E1', 'Signed quote', '2026-03-31', 'Contract', 'o', 'Quote approved. A deposit of $33,000.00 will be required to begin.', share=True, file='E1.pdf'),
        X('E2', 'Check image', '2026-07-02', 'Payment', 'c', 'Pay to the order of Contractor. $33,000.00. Check 107.', share=True, file='E2.png'),
        X('E3', 'Contractor email thread', '2026-08-15', 'Email', 'o', 'The schedule holds. This message may contain privileged information.', share=True, file='E3.html', allow_markers=['privileged']),
        X('E4', 'Memo prepared for counsel', '2026-09-12', 'Memo', 'c', 'Compiled for counsel. Notes on options.', share=False, file='E4.pdf'),
        X('E5', 'Bank statement', '2026-07-10', 'Statement', 'o', 'Account ending 4321. Check 107 posted.', share=False, file='E5.png'),
        X('E6', 'Written refund request', '2026-09-01', 'Letter', 'c', 'We ask for the return of the $33,000.00 deposit. No work has begun.', share=True, file='E6.pdf')],
    facts=[
        F('T1', '2026-03-31', 'The owners approved the quote; it says a deposit is “required to begin.”', 'documented', ['E1'], ['p1', 'p2', 'p3'], ['payment'], outward=True),
        F('T2', '2026-07-02', 'The owners wrote check 107 for the deposit.', 'documented', ['E2'], ['p1', 'p2'], ['payment'], outward=True),
        F('T3', '2026-07-10', 'The check posted to the owners\' account.', 'documented', ['E5'], ['p1'], ['payment'], outward=True),
        F('T4', '2026-08-15', 'The contractor wrote that “the schedule holds.”', 'documented', ['E3'], ['p3'], ['communications'], outward=True),
        F('T5', '2026-09-01', 'The owners sent a written request for the return of the deposit.', 'documented', ['E6'], ['p1', 'p2', 'p3'], ['payment'], outward=True),
        F('T6', '2026-09-12', 'Counsel received a memo from the owners.', 'documented', ['E4'], ['p4'], ['communications'], outward=False),
        F('T7', '2026-09-20', 'The owners report that no work has been done at the property.', 'account', [], ['p1', 'p2'], ['work'], outward=True)],
    intervals=[dict(id='paid', label='From the quote to the written check', a='T1', b='T2')],
    deadlines=[], held_back=[dict(phrase='preservation demand', why='A letter planned by counsel; held until counsel decides.')])
# An estate record that tracks money and authority. It accuses a named person, so it has no outward page (meta.outward is false),
# its labels are roles, not characterizations, and it says whose claim it is. The person building it is not the rights holder.
FULL3 = dict(
    meta=dict(title='Accounts of a parent who died, and an agent under a power of attorney (fictional full example)', product='estate',
              subtitle='Two bank statements, a power of attorney, and what the bank and the court wrote',
              summary=('The bank statements show {sum:by:p3} in transactions they attribute to the agent named in the power of attorney. '
                       'Of that, {sum:after:A1} is dated after the death recorded in fact F2. This record holds {count:facts} dated entries and {count:documents} documents.'),
              ask='An accounting of the accounts, and the return of any money a court finds was not the agent\'s to take', amount='Not entered',
              jurisdiction='Example State (required input)', lawyer='none yet', sent_to_other_side='A records request to the bank', offers='none reported',
              absences=['Any document in which the parent describes the transfers as gifts', 'A medical record from the month the power of attorney was signed'],
              footer='Fictional example. Every name and number is invented.', updated=UPD, asof='2025-10-01', outward=False,
              banned=['stole', 'theft', 'thief', 'mistress', 'gold digger', 'fraud'],
              standing=dict(rights_holder='p2', builder_role='Partner of the heir, helping to organize the papers', permission='The heir asked for this record in writing (exhibit E8).')),
    people=[dict(id='p1', name='Parent', role='The person who died; owned the accounts'), dict(id='p2', name='Heir', role='Child of the parent'),
            dict(id='p3', name='Agent', role='Person named as agent in the power of attorney'), dict(id='p4', name='Bank', role='Holds the accounts'),
            dict(id='p5', name='Administrator', role='Appointed by the court to manage the estate'), dict(id='p6', name='Organizer', role='Partner of the heir; building this record')],
    issues=[dict(id='authority', label='The power of attorney'), dict(id='money', label='Money that moved'), dict(id='records', label='Records requests'), dict(id='estate', label='The estate')],
    lanes=[dict(id='papers', label='Documents and the court'), dict(id='bank', label='The bank')],
    exhibits=[
        X('E1', 'Power of attorney', '2025-03-04', 'Legal document', 't', 'Durable power of attorney for property. I appoint Agent as my agent. Signed by Parent and notarized on March 4, 2025.', share=False, file='E1.pdf'),
        X('E2', 'Death certificate', '2025-06-18', 'Certificate', 't', 'Date of death: June 18, 2025.', share=False, file='E2.pdf'),
        X('E3', 'Bank statement, June 2025', '2025-06-30', 'Statement', 'o',
          'Account ending 0042. 06/02 Online transfer to account ending 7781, initiated by Agent, 8,000.00. 06/20 Cash withdrawal, Agent, 12,500.00. 06/27 Check 311 payable to Agent, 4,000.00.',
          share=False, file='E3.pdf'),
        X('E4', 'Bank statement, July 2025', '2025-07-31', 'Statement', 'o', 'Account ending 0042. 07/08 Online transfer to account ending 7781, initiated by Agent, 15,000.00.', share=False, file='E4.pdf'),
        X('E5', "Heir's records request to the bank", '2025-08-05', 'Letter', 'c', 'Please provide all statements, signature cards, and the power of attorney on file for the account ending 0042.', share=False, file='E5.pdf'),
        X('E6', "Bank's reply", '2025-08-29', 'Letter', 'o', 'We have received your request. Records will be provided to the personal representative of the estate.', share=False, file='E6.pdf'),
        X('E7', 'Court order appointing the administrator', '2025-09-15', 'Court order', 't', 'Administrator is appointed to administer the estate of Parent.', share=False, file='E7.pdf'),
        X('E8', "Heir's note asking for help with the record", '2025-08-01', 'Note', 'c', 'Please help me put the bank papers in order.', share=False, file='E8.pdf'),
        X('E9', 'Second copy of the June statement', '2025-06-30', 'Statement', 'o', 'Account ending 0042. 06/20 Cash withdrawal, Agent, 12,500.00.', fold_into='E3', share=False, file='E9.pdf')],
    facts=[
        F('F1', '2025-03-04', 'The parent signed a “Durable power of attorney for property” naming the agent; the document says it was notarized the same day.', 'documented',
          [dict(ex='E1', quote='Durable power of attorney for property.')], ['p1', 'p3'], ['authority'], lane='papers'),
        F('F2', '2025-06-18', 'The parent died; the death certificate gives the date.', 'documented', [dict(ex='E2', quote='Date of death: June 18, 2025.')], ['p1'], ['estate'], lane='papers'),
        F('F3', '2025-06-30', 'The June statement lists three transactions it attributes to the agent.', 'documented', ['E3'], ['p3', 'p4'], ['money'], lane='bank'),
        F('F4', '2025-07-31', 'The July statement lists an online transfer “initiated by Agent.”', 'documented', [dict(ex='E4', quote='initiated by Agent')], ['p3', 'p4'], ['money'], lane='bank'),
        F('F5', '2025-08-01', 'The heir asked the organizer in writing to help put the bank papers in order.', 'documented', ['E8'], ['p2', 'p6'], ['records'], lane='papers'),
        F('F6', '2025-08-05', 'The heir asked the bank for the statements, signature cards and the power of attorney on file.', 'documented', ['E5'], ['p2', 'p4'], ['records'], lane='bank'),
        F('F7', '2025-08-29', 'The bank wrote that records “will be provided to the personal representative of the estate.”', 'documented', ['E6'], ['p4'], ['records'], lane='bank'),
        F('F8', '2025-09-15', 'The court appointed an administrator for the estate.', 'documented', ['E7'], ['p5'], ['estate'], lane='papers'),
        F('F9', '2025-09-20', 'The heir reports that the agent said the money was a gift from the parent.', 'disputed', [], ['p2', 'p3'], ['money'], lane='bank'),
        F('F10', '2025-09-21', 'Whether the parent understood the power of attorney when signing it is not known.', 'open', [], ['p1'], ['authority'], lane='papers'),
        F('F11', '2025-06-30', 'Second copy of the June statement, showing the cash withdrawal.', 'documented', ['E9'], ['p4'], ['money'], lane='bank', fold_into='F3')],
    authorities=[dict(id='A1', holder='p3', **{'for': 'p1'}, kind='Durable power of attorney for property', ex='E1', **{'from': 'F1'}, to='F2',
                      note='The record places its end at the death in F2. Whether and when the authority ended is for a lawyer to confirm.')],
    ledger=[dict(id='L1', date='2025-06-02', amount='8,000.00', **{'from': 'Account ending 0042'}, to='Account ending 7781', by='p3', method='Online transfer', sources=[dict(ex='E3', loc='06/02')]),
            dict(id='L2', date='2025-06-20', amount='12,500.00', **{'from': 'Account ending 0042'}, to='Cash', by='p3', method='Cash withdrawal', sources=[dict(ex='E3', loc='06/20')]),
            dict(id='L3', date='2025-06-27', amount='4,000.00', **{'from': 'Account ending 0042'}, to='p3', by='p3', method='Check 311', sources=[dict(ex='E3', loc='06/27')],
                 note='The statement shows the payee; it does not show who signed the check.'),
            dict(id='L4', date='2025-07-08', amount='15,000.00', **{'from': 'Account ending 0042'}, to='Account ending 7781', by='p3', method='Online transfer', sources=[dict(ex='E4', loc='07/08')])],
    intervals=[dict(id='death-request', label='From the death to the records request', a='F2', b='F6')],
    deadlines=[], held_back=[dict(phrase='what the heir thinks of the agent', why='Feelings stay out of the record.')])
FULL = [('FULL1', FULL1), ('FULL2', FULL2), ('FULL3', FULL3)]


# ---------- placeholder documents ----------

def _font(size):
    from PIL import ImageFont
    try:
        return ImageFont.load_default(size=size)
    except TypeError:
        return ImageFont.load_default()


def _page(title, text, w=850, h=1100):
    import textwrap
    from PIL import Image, ImageDraw
    im = Image.new('RGB', (w, h), 'white')
    dr = ImageDraw.Draw(im)
    dr.text((50, 50), title, fill='black', font=_font(30))
    y = 120
    for line in textwrap.wrap(text, 52) or ['']:
        dr.text((50, y), line, fill=(30, 30, 30), font=_font(22))
        y += 32
    dr.text((50, h - 70), 'Fictional placeholder. It shows the text the record quotes.', fill=(120, 120, 120), font=_font(16))
    return im


def _exif():
    from PIL import Image
    ex = Image.Exif()
    ex[315] = 'Fictional Person'
    ex[270] = 'Taken at 1 Example Street'
    ex[0x8825] = {1: 'N', 2: (41.0, 52.0, 48.0), 3: 'W', 4: (87.0, 37.0, 12.0)}
    return ex


def write_placeholder(path, ex):
    """A fake document that shows the exhibit's text and carries fake author and location metadata on purpose."""
    from PIL import Image, PngImagePlugin
    ext = os.path.splitext(path)[1].lower()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = ex.get('text') or ex['title']
    if ext == '.pdf':
        pages = [_page(ex['title'], text), _page(ex['title'], 'Page 2 of the fictional document.')]
        pages[0].save(path, 'PDF', save_all=True, append_images=pages[1:], resolution=100.0, author='Fictional Person', subject='1 Example Street, Exampleville',
                      title='Private working title', creator='Fictional Writer')
    elif ext in ('.jpg', '.jpeg'):
        _page(ex['title'], text, 600, 450).save(path, 'JPEG', exif=_exif())
    elif ext == '.png':
        info = PngImagePlugin.PngInfo()
        info.add_text('Author', 'Fictional Person')
        info.add_text('Description', '1 Example Street')
        _page(ex['title'], text, 700, 500).save(path, 'PNG', pnginfo=info)
    elif ext in ('.html', '.htm'):
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(f'<!doctype html><html><head><meta charset="utf-8"><title>{ex["title"]}</title></head><body><h1>{ex["title"]}</h1><p>{text}</p></body></html>')
    elif ext == '.txt':
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write(text + '\n')
    elif ext == '.mp4':
        if not shutil.which('ffmpeg'):
            return False
        r = subprocess.run(['ffmpeg', '-nostdin', '-y', '-v', 'error', '-f', 'lavfi', '-i', 'testsrc=duration=1:size=320x240:rate=10', '-f', 'lavfi', '-i', 'sine=frequency=440:duration=1',
                            '-c:v', 'mpeg4', '-c:a', 'aac', '-shortest', '-metadata', 'title=Private clip title', '-metadata', 'location=+41.8800-087.6200/',
                            '-metadata', 'com.apple.quicktime.location.ISO6709=+41.8800-087.6200/', path], capture_output=True, text=True)
        return r.returncode == 0
    return True


def write_files(outdir, id, rec):
    """Placeholder files next to the record: OUTDIR/<id>-files/. Drops the file name from an exhibit when it cannot be made (no ffmpeg)."""
    root = os.path.join(outdir, f'{id}-files')
    for e in rec['exhibits']:
        for fld in ('file', 'thumb'):
            if e.get(fld):
                target = os.path.join(root, e[fld])
                if fld == 'thumb':
                    from PIL import Image
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    _page(e['title'], e.get('text') or e['title'], 320, 240).save(target, 'JPEG', exif=_exif())
                elif not write_placeholder(target, e):
                    del e['file']
                    e.pop('thumb', None)
                    break
    return root


def all_records():
    return list(B) + list(FULL)


def main(argv=None):
    import argparse
    ap = argparse.ArgumentParser(prog='seed.py', description='Write the 21 invented example records (18 short, 3 full) and their placeholder documents into OUTDIR.',
                                 epilog='Then build one: python3 ../build_views.py OUTDIR/V1.json OUTDIR/V1-inward')
    ap.add_argument('outdir', nargs='?', default='out', help='the folder to write into (made if it is not there); default: out')
    out = ap.parse_args(argv).outdir
    os.makedirs(out, exist_ok=True)
    for id, rec in all_records():
        rec = json.loads(json.dumps(rec))
        write_files(out, id, rec)
        with open(os.path.join(out, f'{id}.json'), 'w', encoding='utf-8') as fh:
            json.dump(rec, fh, indent=1)
    print(f'wrote {len(B)} short records and {len(FULL)} full records to {out}, with placeholder files in {out}/<id>-files/')
    return 0


if __name__ == '__main__':
    sys.exit(main())
