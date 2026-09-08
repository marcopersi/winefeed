package ch.persi.wine.feed.priceservice.model;

import java.time.LocalDate;

/**
 * One flat auction row as read from the staging Excel files.
 * Missing/optional columns are represented as {@code null}.
 */
public record WineAuctionRow(
        String name,
        String producer,
        String region,
        String origin,
        Integer vintage,
        Double deciliters,
        Integer noOfBottles,
        String providerOfferingId,
        String eventIdentifier,
        LocalDate offeringDate,
        Boolean isOhk,
        Double priceMin,
        Double priceMax,
        Double realizedPrice,
        String provider,
        String note
) {
}
