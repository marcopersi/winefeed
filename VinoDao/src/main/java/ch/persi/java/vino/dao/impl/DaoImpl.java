package ch.persi.java.vino.dao.impl;

import ch.persi.java.vino.dao.IDao;
import ch.persi.java.vino.domain.*;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.orm.hibernate5.support.HibernateDaoSupport;

import javax.persistence.NamedQueries;
import javax.persistence.NamedQuery;
import java.io.Serializable;
import java.math.BigDecimal;
import java.util.Collection;
import java.util.Collections;
import java.util.Date;
import java.util.List;

			@NamedQueries({
				@NamedQuery(name = "findByName", query = "Select r from RatingAgency r where r.name=:ratingAgencyName"),
				@NamedQuery(name = "findByCountry", query = "Select w from Wine w where w.country=:countryName")
			})

// FIXME: to be replaced with GenericDao
public class DaoImpl extends HibernateDaoSupport implements IDao {

	private final Logger logging = LoggerFactory.getLogger(getClass());
	
	@Override
	public WineOffering save(WineOffering offering) {
        assert getHibernateTemplate() != null;
        Serializable savedOffering = getHibernateTemplate().save(offering);
		return getHibernateTemplate().get(WineOffering.class, savedOffering);
	}

	@Override
	public RatingAgency save(RatingAgency theRatingAgency) {
        assert getHibernateTemplate() != null;
        Serializable savedRatingAgency = getHibernateTemplate().save(theRatingAgency);
		return getHibernateTemplate().get(RatingAgency.class, savedRatingAgency);
	}

	@Override
	public Rating save(Rating rating) {
        assert getHibernateTemplate() != null;
        Serializable savedRating = getHibernateTemplate().save(rating);
		return getHibernateTemplate().get(Rating.class, savedRating);
	}

	@Override
	public Wine save(Wine wine) {
        assert getHibernateTemplate() != null;
        Serializable savedWine = getHibernateTemplate().save(wine);
		return getHibernateTemplate().get(Wine.class, savedWine);
	}

	@Override
	public Unit save(Unit unit) {
        assert getHibernateTemplate() != null;
        Serializable savedUnit = getHibernateTemplate().save(unit);
		return getHibernateTemplate().get(Unit.class, savedUnit);
	}

	@Override
	public Provider save(Provider provider) {
        assert getHibernateTemplate() != null;
        Serializable savedProvider = getHibernateTemplate().save(provider);
		return getHibernateTemplate().get(Provider.class, savedProvider);
	}

	@Override
	public Offering save(Offering offering) {
        assert getHibernateTemplate() != null;
        Serializable savedOffering = getHibernateTemplate().save(offering);
		return getHibernateTemplate().get(Offering.class, savedOffering);
	}

	@Override
	@SuppressWarnings("rawtypes")
	public RatingAgency findRatingAgencyByName(String theRatingAgency) {
        assert getHibernateTemplate() != null;
        List aRatingAgency = getHibernateTemplate().findByNamedParam("Select r from RatingAgency r where r.ratingAgencyName=:ratingAgencyName", "ratingAgencyName", theRatingAgency);
		logging.debug("Found {} as ratingAgency for string {}",aRatingAgency,theRatingAgency);
		if (!aRatingAgency.isEmpty())
		{
			return (RatingAgency) aRatingAgency.get(0);
		}
		return null;
	}
	
	@Override
	@SuppressWarnings("unchecked")
	public Collection<Wine> findWineByName(String theWineName)
	{
        assert getHibernateTemplate() != null;
        @SuppressWarnings("rawtypes")
		List aWine = getHibernateTemplate().findByNamedParam("Select w from Wine w where w.name=:wineName", "wineName", theWineName);
		logging.info("Found wine {} for string {}",aWine,theWineName);
		return aWine;
		
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public List<WineOffering> getAllWineOfferings() {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().find("Select w from WineOffering w");
	}

	@Override
	@SuppressWarnings({ "unchecked", "rawtypes" })
	public List<WineOffering> findAllWineOfferingsByWine(Wine theWine) {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().findByNamedParam("Select w from WineOffering w where w.wine=:aWine","aWine",theWine);
	}

	@Override
	public Rating findRatingByAgencyAndPoints(RatingAgency theAgency,BigDecimal thePoints) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Unit findUnitByDeciliters(BigDecimal theDeciliters) {
        assert getHibernateTemplate() != null;
        List someFoundUnits = getHibernateTemplate().findByNamedParam("Select u from Unit u where u.deciliters=:Deciliters", "Deciliters", theDeciliters);
		if (!someFoundUnits.isEmpty())
			return (Unit)someFoundUnits.get(0);
		return null;
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Provider findProviderByName(String theProviderName) {
        assert getHibernateTemplate() != null;
        List someFoundProviders = getHibernateTemplate().findByNamedParam("Select p from Provider p where p.name=:ProviderName","ProviderName",theProviderName);
		if (someFoundProviders.size()==1)
		{
			return (Provider)someFoundProviders.get(0);
		}
		return null;
	}

	@Override
	@SuppressWarnings({ "unchecked", "rawtypes" })
	public List<Offering> findAllOfferings() {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().findByNamedQuery("FindAllOfferings");
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public List<Offering> findAllOfferingsByProvider(Provider theProvider) {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().findByNamedParam("Select o from Offering o where o.provider=:provider","provider", theProvider);
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Wine findWineByNameAndYear(String theWineName, int i) {

		String[] theParamNames = new String[] {"WineName", "WineYear"};
		Object[] theParamValues = new Object[2];
		theParamValues[0] = theWineName;
		theParamValues[1] = i;

        assert getHibernateTemplate() != null;
        List someFoundWines = getHibernateTemplate().findByNamedParam("Select w from Wine w where w.name=:WineName and w.vintage=:WineYear",theParamNames,theParamValues);
		if (someFoundWines.size() == 1)
		{
			return (Wine)someFoundWines.get(0);
		}
		return null;
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked", "cast" })
	public List<Wine> findAllWines() {
        assert getHibernateTemplate() != null;
        List someFoundWines = getHibernateTemplate().find("Select w from Wine w");
		return (List<Wine>) someFoundWines;
	}

	@SuppressWarnings({ "rawtypes", "unchecked" })
	@Override
	public List<Wine> findWinesByCountry(String theCountry) {
        assert getHibernateTemplate() != null;
        List someFoundWines = getHibernateTemplate().findByNamedQuery("Select w from Wine w where w.country=:CountryName",theCountry);
		if (!someFoundWines.isEmpty())
		{
			return someFoundWines;
		}
		return Collections.emptyList();
	}

	@Override
	public List<Wine> findWinesByRegion(String theRegion) {
		// TODO Auto-generated method stub
		return Collections.emptyList();
	}

	@Override
	@SuppressWarnings({ "rawtypes", "unchecked" })
	public List<Wine> findWinesByOrigin(String theOrigin) {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().findByNamedParam("Select w from Wine w where w.origin=:origin", "origin", theOrigin);
	}

	@Override
	public Offering findWineByMaxRealizedPrice(Wine theWine) {
		// TODO Auto-generated method stub
		return null;
	}

	@Override
	public List<Offering> findOfferingsByWine(Wine theWine) {
		return Collections.emptyList();
	}

	@Override
	@SuppressWarnings("rawtypes")
	public Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier,Date auctionDate) {
		
		String[] theParamNames = new String[] {"LosNummer", "AuctionDate"};
		Object[] theParamValues = new Object[2];
		theParamValues[0] = theProviderOfferingIdentifier;
		theParamValues[1] = auctionDate;
        assert getHibernateTemplate() != null;
        List returnables = getHibernateTemplate().findByNamedParam("Select o from Offering o where o.providerOfferingId=:LosNummer and o.offeringDate=:AuctionDate", theParamNames, theParamValues);
		
		if (returnables.isEmpty())
		{
			logging.error("There's something wrong , didn't found an offering for id {} and date {}",theProviderOfferingIdentifier, auctionDate);
			return null;
		}
		
		return (Offering)returnables.get(0);
	}

	@Override
	public void update(Offering aFoundOffering) {
        assert getHibernateTemplate() != null;
        getHibernateTemplate().update(aFoundOffering);
	}

	@Override
	public void delete(Object aSavedElement) {
        assert getHibernateTemplate() != null;
        getHibernateTemplate().delete(aSavedElement);
	}

	@SuppressWarnings({ "rawtypes", "unchecked" })
	@Override
	public Collection<Provider> findAllProvider() {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().find("Select p from Provider p");
	}

	@SuppressWarnings({ "rawtypes", "unchecked" })
	@Override
	public Collection<RatingAgency> findAllRatingAgency() {
        assert getHibernateTemplate() != null;
        return (List) getHibernateTemplate().find("Select r from RatingAgency r");
	}

}
