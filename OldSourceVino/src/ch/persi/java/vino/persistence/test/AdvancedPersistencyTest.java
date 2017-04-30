package ch.persi.java.vino.persistence.test;

import java.math.BigDecimal;
import java.util.Date;
import java.util.List;

import junit.framework.TestCase;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;

public class AdvancedPersistencyTest extends TestCase {

    private ClassPathXmlApplicationContext aContext;
    private Wine masseto2001;
    private Wine masseto2006;
    private Provider provider;
    
    @SuppressWarnings("rawtypes")
	private List someSavedObjects;
    
    @SuppressWarnings("unchecked")
	@Override
	public void setUp()
	{
		aContext = new ClassPathXmlApplicationContext("classpath:config.xml");
		IDao dao = (IDao) aContext.getBean("dao");
		
		RatingAgency aRatingAgency = dao.findRatingAgencyByName("Parker");
		if (aRatingAgency == null)
		{
			RatingAgency savedRatingAgency = dao.save(new RatingAgency(new BigDecimal(100),"Parker"));
			someSavedObjects.add(savedRatingAgency);
		}
		
		Unit unit = dao.findUnitByDeciliters(new BigDecimal(7.5));
		if (unit == null) {
			unit = dao.save(new Unit(new BigDecimal(7.5)));
			someSavedObjects.add(unit);
		}
		
		masseto2001 = dao.findWineByNameAndYear("Masseto",2001);

		if (masseto2001 == null)
		{
			masseto2001 = dao.save(new Wine(2001,"MO","Masseto","Bolgheri, Toskana", "Tenuta del'Ornellaia"));
			someSavedObjects.add(masseto2001);
		}

		masseto2006 = dao.findWineByNameAndYear("Masseto",2006);
		if (masseto2006 == null)
		{
			masseto2006 = dao.save(new Wine(2006,"MO","Masseto", "Bolgheri, Toskana", "Tenuta del'Ornellaia"));
			someSavedObjects.add(masseto2006);
		}
		
		provider = dao.findProviderByName("Wermuth SA.");
		if (provider == null)
		{
			Provider savedProvider = dao.save(new Provider("Wermuth SA."));
			someSavedObjects.add(savedProvider);
		}
	}

    @SuppressWarnings("unchecked")
	public void testSave()
    {
    	IDao dao = (IDao)aContext.getBean("dao");
		Unit unit = dao.findUnitByDeciliters(new BigDecimal(7.5));
		Offering offering = new Offering(provider, "1", new BigDecimal(999), new BigDecimal(1800),new Date(), false,1);
		Offering savedOffering = dao.save(offering);
		someSavedObjects.add(savedOffering);
		assertNotNull(savedOffering);

		WineOffering aWineOffering = new WineOffering(masseto2001,unit);
		aWineOffering.setOffering(savedOffering);
		WineOffering savedMasseto2001 = dao.save(aWineOffering);
		someSavedObjects.add(savedMasseto2001);
		assertNotNull(savedMasseto2001);
		
		WineOffering anotherWineOffering = new WineOffering(masseto2006,unit);
		anotherWineOffering.setOffering(savedOffering);
		WineOffering savedMasseto2006 = dao.save(anotherWineOffering);
		someSavedObjects.add(savedMasseto2006);
		assertNotNull(savedMasseto2006);
		System.out.println("Test successfully done");		
    }
    
    @Override
	public void tearDown()
    {
    	if (!someSavedObjects.isEmpty())
    	{
    		IDao dao = (IDao)aContext.getBean("dao");
    		for (Object aSavedElement : someSavedObjects) {
    			dao.delete(aSavedElement);
			}
    	}
    }
}
