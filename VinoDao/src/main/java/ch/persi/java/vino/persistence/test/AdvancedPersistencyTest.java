
package ch.persi.java.vino.persistence.test;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.List;

import org.springframework.context.support.ClassPathXmlApplicationContext;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Rating;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;
import junit.framework.TestCase;

public class AdvancedPersistencyTest extends TestCase {

  private ClassPathXmlApplicationContext aContext;
  private Wine masseto2001;
  private Wine masseto2006;
  private Provider provider;

  @SuppressWarnings("rawtypes")
  private List someSavedObjects;

  private boolean deleteAll;
  private IDao dao;

  @SuppressWarnings({ "unchecked", "rawtypes" })
  @Override
  public void setUp() {
    aContext = new ClassPathXmlApplicationContext("classpath:context.xml");
    someSavedObjects = new ArrayList();

    dao = (IDao)aContext.getBean("dao");

    RatingAgency aRatingAgency = dao.findRatingAgencyByName("Parker");
    if (aRatingAgency == null) {
      aRatingAgency = dao.save(new RatingAgency(new BigDecimal(100), "Parker"));
      someSavedObjects.add(aRatingAgency);
    }

    Unit unit = dao.findUnitByDeciliters(new BigDecimal(7.5));
    if (unit == null) {
      unit = dao.save(new Unit(new BigDecimal(7.5)));
      someSavedObjects.add(unit);
    }

    masseto2001 = dao.findWineByNameAndYear("Masseto", 2001);

    if (masseto2001 == null) {
      Wine wine = new Wine(2001, "MO", "Masseto", "Bolgheri, Toskana", "Tenuta del'Ornellaia");
      wine.addRating(new Rating(aRatingAgency, new BigDecimal(98).setScale(0)));
      masseto2001 = dao.save(wine);
      someSavedObjects.add(masseto2001);
    }

    masseto2006 = dao.findWineByNameAndYear("Masseto", 2006);
    if (masseto2006 == null) {
      Wine wine = new Wine(2006, "MO", "Masseto", "Bolgheri, Toskana", "Tenuta del'Ornellaia");
      wine.addRating(new Rating(aRatingAgency, new BigDecimal(99).setScale(0)));
      masseto2006 = dao.save(wine);
      someSavedObjects.add(masseto2006);
    }

    provider = dao.findProviderByName("Wermuth SA.");
    if (provider == null) {
      provider = dao.save(Provider.WERMUTH);
      someSavedObjects.add(provider);
    }
  }

  @SuppressWarnings("unchecked")
  public void testSave() {
    Unit unit = dao.findUnitByDeciliters(new BigDecimal(7.5));
    Offering offering = new Offering(Provider.WERMUTH.name(), "1", 999, 1800, LocalDate.now(), false, 1);
    Offering savedOffering = dao.save(offering);
    someSavedObjects.add(savedOffering);
    assertNotNull(savedOffering);

    WineOffering aWineOffering = new WineOffering(masseto2001, unit);
    aWineOffering.setOffering(savedOffering);
    WineOffering savedMasseto2001 = dao.save(aWineOffering);
    someSavedObjects.add(savedMasseto2001);
    assertNotNull(savedMasseto2001);

    WineOffering anotherWineOffering = new WineOffering(masseto2006, unit);
    anotherWineOffering.setOffering(savedOffering);
    WineOffering savedMasseto2006 = dao.save(anotherWineOffering);
    someSavedObjects.add(savedMasseto2006);
    assertNotNull(savedMasseto2006);
    System.out.println("Test successfully done");
  }

  public void testSaveOffering() {
    Wine aSavedWine = dao.save(new Wine(2001, "AC/MO", "Masseto", "Bolgheri, Toskana", "Tenuta del'Ornellaia"));

    Unit aSavedUnit = dao.findUnitByDeciliters(new BigDecimal(7.5));
    Provider findProviderByName = dao.findProviderByName("Wermuth SA.");

    Offering aSavedOffering = dao.save(new Offering(findProviderByName.name(), "100", 600, 900, LocalDate.now(), false, 1));
    System.out.println(aSavedOffering.getId());
    assertNotNull(aSavedOffering.getId());

    WineOffering aWineOffering = new WineOffering(aSavedWine, aSavedUnit);
    aWineOffering.setOffering(aSavedOffering);
    WineOffering aSavedWineOffering = dao.save(aWineOffering);
    assertNotNull(aSavedWineOffering);
    System.out.println("Test succeeded !");

    dao.delete(aSavedWineOffering);
    dao.delete(aSavedOffering);
    dao.delete(aSavedWine);
  }

  public void testDeleteAll() {
    if (deleteAll) {
      if (someSavedObjects != null && !someSavedObjects.isEmpty()) {
        for (Object aSavedElement : someSavedObjects) {
          dao.delete(aSavedElement);
        }
      }
    }
  }

}
