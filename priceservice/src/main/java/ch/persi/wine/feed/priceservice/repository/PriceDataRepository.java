package ch.persi.wine.feed.priceservice.repository;

import ch.persi.wine.feed.priceservice.data.PriceData;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface PriceDataRepository extends JpaRepository<PriceData, Long> {
    List<PriceData> findByColumn1Containing(String keyword);
}
