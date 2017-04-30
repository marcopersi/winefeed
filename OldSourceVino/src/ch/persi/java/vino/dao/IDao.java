package ch.persi.java.vino.dao;

import java.math.BigDecimal;
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
	public WineOffering save(WineOffering offering);
	public List<WineOffering> getAllWineOfferings();
	public List<WineOffering> findAllWineOfferingsByWine(Wine theWine);
	
	// Rating
	public Rating save(Rating rating);
	public Rating findRatingByAgencyAndPoints(RatingAgency theAgency,BigDecimal thePoints);
	
	// unit
	public Unit save(Unit unit);
	public Unit findUnitByDeciliters(BigDecimal theDeciliters);
	
	// Provider
	public Provider save(Provider provider);
	public Provider findProviderByName(String theProviderName);
	
	// offerings
	public Offering save(Offering offering);
	public List<Offering> findAllOfferings();
	public List<Offering> findAllOfferingsByProvider(Provider theProvider);
	
	// rating agency
	public RatingAgency save(RatingAgency ratingAgency);
	public RatingAgency findRatingAgencyByName(String string);
	
	// wine
	public Wine save(Wine wine);
	public Wine findWineByNameAndYear(String string, int i);
	public List<Wine> findAllWines();
	public List<Wine> findWinesByCountry(String theCountry);
	public List<Wine> findWinesByRegion(String theRegion);
	public List<Wine> findWinesByOrigin(String theOrigin);
	
	// cross domains
	public Offering findWineByMaxRealizedPrice(Wine theWine);
	public List<Offering> findOfferingsByWine(Wine theWine);
	public Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier,
			Date auctionDate);
	public void update(Offering aFoundOffering);
	public void delete(Object aSavedElement);
	
}
