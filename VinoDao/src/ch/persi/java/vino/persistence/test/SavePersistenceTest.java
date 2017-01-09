package ch.persi.java.vino.persistence.test;

import java.math.BigDecimal;
import java.util.Date;

import junit.framework.TestCase;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;

public class SavePersistenceTest extends TestCase {

	private ClassPathXmlApplicationContext context = null;
	private RatingAgency ratingAgency;
	
	@Override
	public void setUp()
	{
		context = new ClassPathXmlApplicationContext("classpath:context.xml");
		IDao dao = (IDao)context.getBean("dao");

		ratingAgency = dao.findRatingAgencyByName("Parker");
		if (ratingAgency == null)
		{
			throw new IllegalStateException("no parker rating agency in database, please run db init job !");
		}
		
	}

	public void testSaveOffering()
	{
		IDao dao = (IDao)context.getBean("dao");

		Wine aSavedWine = dao.save(new Wine(2001,"AC/MO","Masseto", "Bolgheri, Toskana", "Tenuta del'Ornellaia"));

		Unit aSavedUnit= dao.findUnitByDeciliters(new BigDecimal(7.5));
		Provider findProviderByName = dao.findProviderByName("Wermuth SA.");
		
		Offering aSavedOffering = dao.save(new Offering(findProviderByName, "100",new BigDecimal(600), new BigDecimal(900), new Date(),false,1));
		System.out.println(aSavedOffering.getId());
		
		WineOffering aWineOffering = new WineOffering(aSavedWine, aSavedUnit);
		aWineOffering.setOffering(aSavedOffering);
		WineOffering aSavedWineOffering = dao.save(aWineOffering);
		assertNotNull(aSavedWineOffering);
		System.out.println("Test succeeded !");

		dao.delete(aSavedWineOffering);
		dao.delete(aSavedOffering);
		dao.delete(aSavedWine);
	}
	
}