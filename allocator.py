from itertools import product

# Compute the total expected cost of a specific allocation (split)
def compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue):
    executed = 0         # Total shares that were actually executed
    cash_spent = 0       # Total money spent to execute the order

    # Loop over each venue and calculate execution cost
    for i in range(len(venues)):
        venue = venues[i]
        qty = split[i]   # Shares allocated to this venue
        exe = min(qty, venue['ask_size'])  # Only as many shares as are available at the ask
        executed += exe
        cash_spent += exe * (venue['ask'] + venue['fee'])  # Pay ask price + fee

        # If more shares were sent than filled, subtract the rebate for excess (not filled) shares
        maker_rebate = max(qty - exe, 0) * venue['rebate']
        cash_spent -= maker_rebate

    # Compute penalties for overfill and underfill
    underfill = max(order_size - executed, 0)
    overfill = max(executed - order_size, 0)
    risk_pen = theta_queue * (underfill + overfill)  # Queue-risk penalty
    cost_pen = lambda_under * underfill + lambda_over * overfill  # Execution cost penalty

    return cash_spent + risk_pen + cost_pen  # Total cost = cash + penalties

# Allocate the order size across venues using a brute-force grid search
def allocate(order_size, venues, lambda_over, lambda_under, theta_queue):
    step = 500  # Step size for search (e.g., try 0, 500, 1000...)
    num_venues = len(venues)

    if num_venues == 0:
        return [0] * num_venues, float('inf')  # Edge case: no venues available

    best_cost = float('inf')
    best_split = None

    # Generate all combinations of splits across venues where total shares == order_size
    for split in product(range(0, order_size + 1, step), repeat=num_venues):
        if sum(split) != order_size:
            continue  # Skip splits that don't exactly add up to the order size

        # Compute cost of current allocation
        cost = compute_cost(split, venues, order_size, lambda_over, lambda_under, theta_queue)

        # Keep track of the best (lowest cost) split found
        if cost < best_cost:
            best_cost = cost
            best_split = split

    return best_split, best_cost  # Return the best allocation and its associated cost
