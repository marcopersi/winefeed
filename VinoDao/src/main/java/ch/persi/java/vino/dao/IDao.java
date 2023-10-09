package ch.persi.java.vino.dao;

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

public interface IDao {

	// Wineofferings
	 WineOffering save(WineOffering offering);
	 List<WineOffering> getAllWineOfferings();
	 List<WineOffering> findAllWineOfferingsByWine(Wine theWine);
	
	// Rating
	 Rating save(Rating rating);
	 Rating findRatingByAgencyAndPoints(RatingAgency theAgency,BigDecimal thePoints);
	
	// unit
	 Unit save(Unit unit);
	 Unit findUnitByDeciliters(BigDecimal theDeciliters);
	
	// Provider
	 Provider save(Provider provider);
	 Provider findProviderByName(String theProviderName);
	
	// offerings
	 Offering save(Offering offering);
	 List<Offering> findAllOfferings();
	 List<Offering> findAllOfferingsByProvider(Provider theProvider);
	
	// rating agency
	 RatingAgency save(RatingAgency ratingAgency);
	 RatingAgency findRatingAgencyByName(String string);
	
	// wine
	 Wine save(Wine wine);
	 Wine findWineByNameAndYear(String string, int i);
	 List<Wine> findAllWines();
	 List<Wine> findWinesByCountry(String theCountry);
	 List<Wine> findWinesByRegion(String theRegion);
	 List<Wine> findWinesByOrigin(String theOrigin);
	
	// cross domains
	 Offering findWineByMaxRealizedPrice(Wine theWine);
	 List<Offering> findOfferingsByWine(Wine theWine);
	 Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier,
			Date auctionDate);
	 void update(Offering aFoundOffering);
	 void delete(Object aSavedElement);
	 Collection<Provider> findAllProvider();
	 Collection<RatingAgency> findAllRatingAgency();
	 Collection<Wine> findWineByName(String theWineName);
	
	
}
