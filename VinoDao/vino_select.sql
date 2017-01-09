SELECT 
  wine."year", 
  wine."name" 
FROM 
  public.wine 
WHERE 
  wine."name" like ('%Yquem') 
ORDER BY 
  wine."year" DESC;