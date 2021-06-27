package com.persi.winefeed.priceservice;

import ch.persi.java.vino.domain.*;
import com.persi.winefeed.priceservice.api.WinePriceService;

import java.math.BigDecimal;
import java.util.Collection;
import java.util.Date;
import java.util.List;

public class WinePriceServiceImpl implements WinePriceService {
    @Override
    public Collection<Provider> findAllProvider() {
        return null;
    }

    @Override
    public Collection<RatingAgency> findAllRatingAgency() {
        return null;
    }

    @Override
    public Collection<Wine> findWineByName(String theWineName) {
        return null;
    }

    @Override
    public Collection<WineOffering> findWineOfferingByWine(Wine theWine) {
        return null;
    }

    @Override
    public Collection<WineOffering> findWineOfferingByWineName(String theWineName) {
        return null;
    }

    @Override
    public Rating findRatingByAgencyAndPoints(RatingAgency theAgency, BigDecimal thePoints) {
        return null;
    }

    @Override
    public Unit findUnitByDeciliters(BigDecimal theDeciliters) {
        return null;
    }

    @Override
    public Provider findProviderByName(String theProviderName) {
        return null;
    }

    @Override
    public List<Offering> findAllOfferings() {
        return null;
    }

    @Override
    public List<Offering> findAllOfferingsByProvider(Provider theProvider) {
        return null;
    }

    @Override
    public RatingAgency findRatingAgencyByName(String theRatingAgencyName) {
        return null;
    }

    @Override
    public List<Wine> findAllWines() {
        return null;
    }

    @Override
    public List<Wine> findWinesByCountry(String theCountry) {
        return null;
    }

    @Override
    public List<Wine> findWinesByRegion(String theRegion) {
        return null;
    }

    @Override
    public List<Wine> findWinesByOrigin(String theOrigin) {
        return null;
    }

    @Override
    public Offering findWineByMaxRealizedPrice(Wine theWine) {
        return null;
    }

    @Override
    public List<Offering> findOfferingsByWine(Wine theWine) {
        return null;
    }

    @Override
    public Offering findOfferingByLotNumberAndDate(String theProviderOfferingIdentifier, Date theAuctionDate) {
        return null;
    }

    @Override
    public Wine findWineByNameAndYear(String theWineName, int theVintage) {
        return null;
    }
}
