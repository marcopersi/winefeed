package ch.persi.java.vino.dataservice;

import java.math.BigDecimal;
import java.util.Collection;
import java.util.Date;
import java.util.List;

import ch.persi.java.vino.domain.Offering;
import ch.persi.java.vino.domain.Provider;
import ch.persi.java.vino.domain.Rating;
import ch.persi.java.vino.domain.RatingAgency;
import ch.persi.java.vino.domain.Unit;
import ch.persi.java.vino.domain.Wine;
import ch.persi.java.vino.domain.WineOffering;

public interface DataService {

	/**
	 * 
	 * @return all providers available in the system
	 */
	Collection<Provider> findAllProvider();

	Collection<RatingAgency> findAllRatingAgency();
	
	Collection<Wine> findWineByName(String theWineName);
	
	Collection<WineOffering> findWineOfferingByWine(Wine theWine);
	
	Collection<WineOffering> findWineOfferingByWineName(String theWineName);

	Rating findRatingByAgencyAndPoints(RatingAgency theAgency,
			BigDecimal thePoints);

	Unit findUnitByDeciliters(BigDecimal theDeciliters);

	Provider findProviderByName(String theProviderName);

	List<Offering> findAllOfferings();

	List<Offering> findAllOfferingsByProvider(Provider theProvider);

	RatingAgency findRatingAgencyByName(String theRatingAgencyName);

	List<Wine> findAllWines();

	List<Wine> findWinesByCountry(String theCountry);

	List<Wine> findWinesByRegion(String theRegion);

	List<Wine> findWinesByOrigin(String theOrigin);

	Offering findWineByMaxRealizedPrice(Wine theWine);

	List<Offering> findOfferingsByWine(Wine theWine);

	Offering findOfferingByLotNumberAndDate(
			String theProviderOfferingIdentifier, Date theAuctionDate);

	Wine findWineByNameAndYear(String theWineName, int theVintage);
}
