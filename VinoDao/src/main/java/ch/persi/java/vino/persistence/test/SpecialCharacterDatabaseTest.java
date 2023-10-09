package ch.persi.java.vino.persistence.test;

import java.math.BigDecimal;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Rating;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Wine;
import junit.framework.TestCase;

public class SpecialCharacterDatabaseTest extends TestCase {
 // Ch�teau Cos d�Estournel
	
	private ClassPathXmlApplicationContext context = null;
	private RatingAgency ratingAgency;
	private Rating rating;
	
	@Override
	public void setUp()
	{
		context = new ClassPathXmlApplicationContext("classpath:context.xml");
		IDao dao = (IDao)context.getBean("dao");

		ratingAgency = dao.findRatingAgencyByName("Parker");
		if (ratingAgency == null)
		{
			ratingAgency = dao.save(new RatingAgency(new BigDecimal(100),"Parker"));
		}
		
		rating = dao.findRatingByAgencyAndPoints(ratingAgency, new BigDecimal(99));
		if (rating == null)
		{
			dao.save(new Rating(ratingAgency, new BigDecimal(99)));
		}
	}

	
	/**
	 * Tests if a wine containing a special character as ' in its name may be saved and read again
	 */
	public void testSaveAndReadSpecialCharacterWine()
	{
		IDao dao = (IDao)context.getBean("dao");

		Wine aSavedWine = dao.save(new Wine(2001,"MO","Château Cos d'Estournel", "Rhone,bla", "froggies,france"));
		assertNotNull(aSavedWine);
		
		dao.delete(aSavedWine);
	}
	
}
