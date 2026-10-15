INSERT INTO benchmark_aggregate
(
    industry,
    region,
    size_band,
    peer_count,
    peer_25th,
    peer_median,
    peer_75th
)
VALUES
('Technology', 'West', 'Large', 20, 65.20, 76.40, 88.10),
('Technology', 'West', 'Medium', 18, 61.30, 72.50, 84.70),
('Technology', 'North', 'Large', 16, 62.50, 75.10, 87.30),
('Finance', 'West', 'Large', 15, 60.10, 71.20, 83.50),
('Finance', 'North', 'Medium', 19, 64.20, 73.60, 85.40),
('Healthcare', 'West', 'Large', 17, 63.40, 74.80, 86.20),
('Healthcare', 'South', 'Medium', 15, 58.70, 69.90, 81.50),

-- PG-27 test case: fewer than 10 peers
('Finance', 'West', 'Small', 8, 55.00, 63.00, 72.00);