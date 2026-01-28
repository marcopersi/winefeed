-- Insert standard wine units
INSERT INTO public.unit (name, deciliters) VALUES
('Half Bottle', 3.75),
('Standard Bottle', 7.5),
('Magnum', 15.0),
('Double Magnum', 30.0),
('Jeroboam', 45.0), -- 4.5L
('Imperial', 60.0), -- 6L
('Salmanazar', 90.0), -- 9L
('Balthazar', 120.0), -- 12L
('Nebuchadnezzar', 150.0), -- 15L
('Melchior', 180.0) -- 18L
ON CONFLICT (name) DO NOTHING;

-- Insert providers
INSERT INTO public.provider (name, website, country) VALUES
('Steinfels', 'https://steinfels.ch', 'Switzerland'),
('Excel Import', NULL, NULL)
ON CONFLICT (name) DO NOTHING;
