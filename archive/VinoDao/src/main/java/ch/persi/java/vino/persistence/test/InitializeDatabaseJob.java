
package ch.persi.java.vino.persistence.test;

import java.math.BigDecimal;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import junit.framework.TestCase;

public class InitializeDatabaseJob extends TestCase {

  private ClassPathXmlApplicationContext aContext;
  private IDao dao;

  @Override
  protected void setUp() throws Exception {
    super.setUp();
    aContext = new ClassPathXmlApplicationContext("classpath:context.xml");
    dao = (IDao)aContext.getBean("dao");
  }

  public void testInitProvider() {
    dao.save(Provider.WERMUTH);
    dao.save(Provider.STEINFELS);
    dao.save(Provider.WEINBOERSE);
    dao.save(Provider.SOTHEBYS);
  }

  public void testInitUnits() {
    dao.save(new Unit(new BigDecimal(3.75)));
    dao.save(new Unit(new BigDecimal(7.5)));
    dao.save(new Unit(new BigDecimal(15)));
    dao.save(new Unit(new BigDecimal(30)));
    dao.save(new Unit(new BigDecimal(45)));
    dao.save(new Unit(new BigDecimal(60)));
  }

  public void testInitRatingAgencies() {
    dao.save(new RatingAgency(new BigDecimal(100), "Parker"));
    dao.save(new RatingAgency(new BigDecimal(100), "Weinwisser"));
    dao.save(new RatingAgency(new BigDecimal(100), "Falstaff"));
    dao.save(new RatingAgency(new BigDecimal(20), "Gabriel"));
  }

}
