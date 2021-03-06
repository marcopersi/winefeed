package ch.persi.java.vino.dao;

import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Date;
import java.util.List;

import org.hibernate.annotations.NamedQuery;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.orm.hibernate3.support.HibernateDaoSupport;

import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Rating;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;

@NamedQuery(name="findByname", query="Select r from RatingAgency r where r.name=:ratingAgencyName")
// FIXME: to be replaced with GenericDao
public class DaoImpl extends HibernateDaoSupport implements IDao {

	private final Logger logger = LoggerFactory.getLogger(getClass());
	
	@Override
	public WineOffering save(WineOffering offering) {
		Serializable savedOffering = getHibernateTemplate().save(offering);	
		return getHibernateTemplate().get(WineOffering.class, savedOffering);
	}

	@Override
	public RatingAgency save(RatingAgency theRatingAgency) {
		Serializable savedRatingAgency = getHibernateTemplate().save(theRatingAgency);	
		return getHibernateTemplate().get(RatingAgency.class, savedRatingAgency);
	}

	@Override
	public Rating save(Rating rating) {
		Serializable savedRating = getHibernateTemplate().save(rating);	
		return getHibernateTemplate().get(Rating.class, savedRating);
	}

	@Override
	public Wine save(Wine wine) {
		Serializable savedWine = getHibernateTemplate().save(wine);	
		return getHibernateTemplate().get(Wine.class, savedWine);
	}

	@Override
	public Unit save(Unit unit) {
		Serializable savedUnit = getHibernateTemplate().save(unit);	
		return getHibernateTemplate().get(Unit.class, savedUnit);
	}

	@Override
	public Provider save(Provider provider) {
		Serializable savedProvider = getHibernateTemplate().save(provider);	
		return getHibernateTemplate().get(Provider.class, savedProvider);
	}

	@Override
	public Offering save(Offering offering) {
		Serializable savedOffering = getHibernateTemplate().save(offering);	
		return getHibernateTemplate().get(Offering.class, savedOffering);
	}

	@Override
	@SuppressWarnings("rawtypes")
	public RatingAgency findRatingAgencyByName(String theRatingAgency) {
		List aRatingAgency = getHibernateTemplate().findByNamedParam("Select r from RatingAgency r where r.ratingAgencyName=:ratingAgencyName", "ratingAgencyName", theRatingAgency);
		logger.debug("Found {0} as ratingAgency for string {1}",aRatingAgency,theRatingAgency);
		if (aRatingAgency.size()>=1)
		{
			return (RatingAgency) aRatingAgency.get(0);
		}
		return null;
	}
	
	public Wine findWineByName(String theWineName)
	{
		@SuppressWarnings("rawtypes")
		List aWine = getHibernateTemplate().findByNamedParam("Select w from Wine w where w.name=:wineName", "wineName", theWineName);
		logger.info("Found wine {0} for string {1}",aWine,theWineName);

		if (aWine.size()>=1)
		{
			return (Wine) aWine.get(0);
		}
		return null;
		
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked", "cast" })
	public List<WineOffering> getAllWineOfferings() {
		List someFoundWineOfferings = getHibernateTemplate().find("Select w from WineOffering w");
		return (List<WineOffering>) someFoundWineOfferings;
	}

	@Override
	@SuppressWarnings({ "unchecked", "cast", "rawtypes" })
	public List<WineOffering> findAllWineOfferingsByWine(Wine theWine) {
		List someFoundWineOfferings = getHibernateTemplate().findByNamedParam("Select w from WineOffering w where w.wine_id=:wineId", "wineId", theWine.getId());
		return (List<WineOffering>) someFoundWineOfferings;
	}

	@Override
	public Rating findRatingByAgencyAndPoints(RatingAgency theAgency,BigDecimal thePoints) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Unit findUnitByDeciliters(BigDecimal theDeciliters) {
		List someFoundUnits = getHibernateTemplate().findByNamedParam("Select u from Unit u where u.deciliters=:Deciliters", "Deciliters", theDeciliters);
		if (someFoundUnits != null && someFoundUnits.size()>=1)
		{
			return (Unit)someFoundUnits.get(0);
		}
		return null;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Provider findProviderByName(String theProviderName) {
		List someFoundProviders = getHibernateTemplate().findByNamedParam("Select p from Provider p where p.name=:ProviderName","ProviderName",theProviderName);
		if (someFoundProviders != null && someFoundProviders.size()==1)
		{
			return (Provider)someFoundProviders.get(0);
		}
		return null;
	}

	@Override
	@SuppressWarnings({ "unchecked", "cast", "rawtypes" })
	public List<Offering> findAllOfferings() {
		List someFoundOfferings = getHibernateTemplate().findByNamedQuery("FindAllOfferings");
		return (List<Offering>) someFoundOfferings;
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked", "cast" })
	public List<Offering> findAllOfferingsByProvider(Provider theProvider) {
		List someFoundOfferings = getHibernateTemplate().findByNamedParam("Select o from Offering o where o.provider=:provider","provider", theProvider);
		return (List<Offering>) someFoundOfferings;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Wine findWineByNameAndYear(String theWineName, int i) {

		String[] theParamNames = new String[] {"WineName", "WineYear"};
		Object[] theParamValues = new Object[2];
		theParamValues[0] = theWineName;
		theParamValues[1] = i;
		
		List someFoundWines = getHibernateTemplate().findByNamedParam("Select w from Wine w where w.name=:WineName and w.vintage=:WineYear",theParamNames,theParamValues);
		if (someFoundWines != null && someFoundWines.size()==1)
		{
			return (Wine)someFoundWines.get(0);
		}
		return null;
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked", "cast" })
	public List<Wine> findAllWines() {
		List someFoundWines = getHibernateTemplate().find("Select w from Wine w");
		return (List<Wine>) someFoundWines;
	}

	@Override
	public List<Wine> findWinesByCountry(String theCountry) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public List<Wine> findWinesByRegion(String theRegion) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked", "cast" })
	public List<Wine> findWinesByOrigin(String theOrigin) {
		List someFoundWines = getHibernateTemplate().findByNamedParam("Select w from Wine w where w.origin=:origin", "origin", theOrigin);
		return (List<Wine>) someFoundWines;
	}

	@Override
	public Offering findWineByMaxRealizedPrice(Wine theWine) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public List<Offering> findOfferingsByWine(Wine theWine) {
		return null;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier,Date auctionDate) {
		
		String[] theParamNames = new String[] {"LosNummer", "AuctionDate"};
		Object[] theParamValues = new Object[2];
		theParamValues[0] = theProviderOfferingIdentifier;
		theParamValues[1] = auctionDate;
		List returnables = getHibernateTemplate().findByNamedParam("Select o from Offering o where o.providerOfferingId=:LosNummer and o.offeringDate=:AuctionDate", theParamNames, theParamValues);
		
		if (returnables == null || returnables.size()==0)
		{
			logger.error("There's something wrong , didn't found an offering for id '" + theProviderOfferingIdentifier + "' and date: '" + auctionDate + "'");
			return null;
		}
		
		return (Offering)returnables.get(0);
	}

	@Override
	public void update(Offering aFoundOffering) {
		getHibernateTemplate().update(aFoundOffering);
	}

	@Override
	public void delete(Object aSavedElement) {
		getHibernateTemplate().delete(aSavedElement);
	}

}
