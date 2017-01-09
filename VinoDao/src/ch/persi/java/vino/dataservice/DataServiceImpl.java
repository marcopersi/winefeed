package ch.persi.java.vino.dataservice;

import java.math.BigDecimal;
import java.util.ArrayList;
import java.util.Collection;
import java.util.Date;
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
/**
 * 
 * @author PEM
 * This API is the VINO data service API, it provides operations to get data related to the vino prices.
 * There are no operations to edit any data.
 */
public class DataServiceImpl implements DataService {

	IDao daoService = (IDao)new ClassPathXmlApplicationContext("context.xml").getBean("dao");
	
	@Override
	public Collection<Provider> findAllProvider(){
		return daoService.findAllProvider();
	}

	@Override
	public Collection<RatingAgency> findAllRatingAgency() {
		return daoService.findAllRatingAgency();
	}

	@Override
	public Collection<Wine> findWineByName(String theWineName) {
		return daoService.findWineByName(theWineName);
	}

	@Override
	public Collection<WineOffering> findWineOfferingByWine(Wine theWine) {
		return daoService.findAllWineOfferingsByWine(theWine);
	}

	@Override
	public Collection<WineOffering> findWineOfferingByWineName(String theWineName) {

		Collection<Wine> findWineByName = daoService.findWineByName(theWineName);
		Collection<WineOffering> someFoundWineOfferings = new ArrayList<>();
		if (findWineByName != null && findWineByName.size()>0)
		{
			for (Wine wine : findWineByName) {
				someFoundWineOfferings.addAll(daoService.findAllWineOfferingsByWine(wine));
			}
		}
		return someFoundWineOfferings;
	}
	
	// Rating
	@Override
	public Rating findRatingByAgencyAndPoints(RatingAgency theAgency,BigDecimal thePoints){
		 return daoService.findRatingByAgencyAndPoints(theAgency, thePoints);
	 };
	
	// unit
	 @Override
	 public Unit findUnitByDeciliters(BigDecimal theDeciliters){
		 return daoService.findUnitByDeciliters(theDeciliters);
	 };
	
	// Provider
	 @Override
	 public Provider findProviderByName(String theProviderName)
	 {
		 return daoService.findProviderByName(theProviderName);
	 };
	
	// offerings
	 @Override
	 public List<Offering> findAllOfferings()
	 {
		 return daoService.findAllOfferings();
	 };
	 
	 @Override
	 public List<Offering> findAllOfferingsByProvider(Provider theProvider){
		 return daoService.findAllOfferingsByProvider(theProvider);
	 };
	
	// rating agency
	 @Override
	 public RatingAgency findRatingAgencyByName(String theRatingAgencyName){
		 return daoService.findRatingAgencyByName(theRatingAgencyName);
	 };
	
	// wine
	 @Override
	 public List<Wine> findAllWines(){
		 return daoService.findAllWines();
	 };
	 
	 @Override
	 public List<Wine> findWinesByCountry(String theCountry){
		 return daoService.findWinesByCountry(theCountry);
	 };

	 @Override
	 public List<Wine> findWinesByRegion(String theRegion){
		 return daoService.findWinesByRegion(theRegion);
	 };
	 
	 @Override
	 public List<Wine> findWinesByOrigin(String theOrigin){
		 return daoService.findWinesByOrigin(theOrigin);
	 };
	
	// cross domains
	 @Override
	 public Offering findWineByMaxRealizedPrice(Wine theWine){
		 return daoService.findWineByMaxRealizedPrice(theWine);
	 };
	 
	 @Override
	 public List<Offering> findOfferingsByWine(Wine theWine){
		 return daoService.findOfferingsByWine(theWine);
	 };
	 
	 @Override
	 public Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier,Date theAuctionDate){
		 return daoService.findOfferingByLotNumberAndDate(theProviderOfferingIdentifier, theAuctionDate);
	 }

	@Override
	public Wine findWineByNameAndYear(String theWineName, int theVintage) {
		return daoService.findWineByNameAndYear(theWineName, theVintage);
	};
}
