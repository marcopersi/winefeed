package ch.persi.java.vino.persistence.test;

import junit.framework.TestCase;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Wine;

public class DaoReadTests extends TestCase {

	private IDao dao = null;
	
	@Override
	public void setUp()
	{
		ClassPathXmlApplicationContext context = new ClassPathXmlApplicationContext("classpath:config.xml");
		dao = (IDao)context.getBean("dao");

	}

	public void testFindWineByName()
	{
//		Wine aFoundWine = dao.findWineByNameAndYear("Masseto",2001);
//		assertNotNull(aFoundWine);
		Wine aLafite = dao.findWineByNameAndYear("Ch‰teau Mouton Rothschild",1982);
		assertNotNull(aLafite);
		System.out.println(aLafite);
	}
}
