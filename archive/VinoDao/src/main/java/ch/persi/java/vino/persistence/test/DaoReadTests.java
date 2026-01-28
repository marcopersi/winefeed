package ch.persi.java.vino.persistence.test;

import java.util.Collection;
import java.util.List;

import junit.framework.TestCase;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;
import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;

public class DaoReadTests extends TestCase {

	private IDao dao = null;
	private ClassPathXmlApplicationContext context;
	
	@Override
	@Before
	public void setUp()
	{
		context = new ClassPathXmlApplicationContext("classpath:context.xml");
		dao = (IDao)context.getBean("dao");
	}

	@Test
	public void testFindWineByName()
	{
//		Wine aFoundWine = dao.findWineByNameAndYear("Masseto",2001);
//		assertNotNull(aFoundWine);
		Wine aLafite = dao.findWineByNameAndYear("Château Mouton Rothschild",1982);
		assertNotNull(aLafite);
		System.out.println(aLafite);
	}
	
	@Test
	public void testFindAllWineOfferingsByWineName()
	{
		Collection<Wine> findWineByName = dao.findWineByName("Masseto");
		for (Wine wine : findWineByName) {
			List<WineOffering> findAllWineOfferingsByWine = dao.findAllWineOfferingsByWine(wine);
			for (WineOffering wineOffering : findAllWineOfferingsByWine) {
				System.out.println("Found Offering: " + wineOffering + " for wine: " + wine);
			}
		}
	}

	@Override
	@After
	public void tearDown()
	{
		context.close();
	}
}
