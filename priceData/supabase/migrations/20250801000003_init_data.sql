-- Initial data for providers and rating agencies
-- Based on your existing database setup

-- Insert providers
INSERT INTO public.provider (id, name) VALUES 
(nextval('provider_id_seq'), 'Wermuth SA'),
(nextval('provider_id_seq'), 'Steinfels'),
(nextval('provider_id_seq'), 'Weinbörse'),
(nextval('provider_id_seq'), 'Sothebys');

-- Insert rating agencies with your specific setup
INSERT INTO public.ratingagency (id, ratingagencyname, maxpoints) VALUES 
(nextval('ratingagency_id_seq'), 'Parker', 100),
(nextval('ratingagency_id_seq'), 'Gabriel', 20),
(nextval('ratingagency_id_seq'), 'Weinwisser', 100),
(nextval('ratingagency_id_seq'), 'Falstaff', 100);

-- Clear any existing default rating agencies that might conflict
DELETE FROM public.ratingagency WHERE ratingagencyname IN (
    'Robert Parker / Wine Advocate',
    'Wine Spectator', 
    'James Suckling',
    'Jancis Robinson',
    'Antonio Galloni / Vinous',
    'Decanter',
    'Vinum',
    'Wine Enthusiast',
    'Bettane & Desseauve'
);
