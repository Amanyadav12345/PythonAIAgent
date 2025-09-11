"""
Truck-specific tools for rolling radius calculations and logistics operations
"""
import math
from langchain.tools import tool

@tool
def calculate_rolling_radius(tire_size: str) -> str:
    """
    Calculate rolling radius for truck tires from tire size notation.
    
    Args:
        tire_size: Tire size in format like "295/80R22.5" or "11R22.5"
        
    Returns:
        Rolling radius calculation details including static radius, loaded radius, and rolling radius
    """
    try:
        tire_size = tire_size.strip().upper()
        
        # Handle different tire size formats
        if 'R' in tire_size and '/' in tire_size:
            # Format: 295/80R22.5
            parts = tire_size.split('/')
            width_mm = int(parts[0])
            
            ratio_and_wheel = parts[1].split('R')
            aspect_ratio = int(ratio_and_wheel[0])
            wheel_diameter_inches = float(ratio_and_wheel[1])
            
        elif 'R' in tire_size and tire_size.count('R') == 1:
            # Format: 11R22.5 (cross-ply equivalent)
            parts = tire_size.split('R')
            # Convert cross-ply to radial equivalent
            cross_ply_width = float(parts[0])
            wheel_diameter_inches = float(parts[1])
            
            # Approximate conversions for cross-ply
            width_mm = int(cross_ply_width * 25.4)  # Convert inches to mm
            aspect_ratio = 80  # Common aspect ratio for cross-ply equivalents
            
        else:
            return f"Error: Unsupported tire size format '{tire_size}'. Use formats like '295/80R22.5' or '11R22.5'"
        
        # Calculate sidewall height
        sidewall_height_mm = (width_mm * aspect_ratio) / 100
        
        # Convert wheel diameter to mm
        wheel_radius_mm = (wheel_diameter_inches * 25.4) / 2
        
        # Calculate static radius (wheel radius + sidewall height)
        static_radius_mm = wheel_radius_mm + sidewall_height_mm
        
        # Calculate loaded radius (typically 95-97% of static radius for truck tires)
        loaded_radius_mm = static_radius_mm * 0.96
        
        # Calculate rolling radius (typically 97-99% of static radius for truck tires)
        rolling_radius_mm = static_radius_mm * 0.98
        
        # Calculate circumference
        rolling_circumference_mm = 2 * math.pi * rolling_radius_mm
        
        # Convert to different units for practical use
        results = {
            "tire_size": tire_size,
            "width_mm": width_mm,
            "aspect_ratio": aspect_ratio,
            "wheel_diameter_inches": wheel_diameter_inches,
            "sidewall_height_mm": round(sidewall_height_mm, 1),
            "static_radius_mm": round(static_radius_mm, 1),
            "static_radius_inches": round(static_radius_mm / 25.4, 2),
            "loaded_radius_mm": round(loaded_radius_mm, 1),
            "loaded_radius_inches": round(loaded_radius_mm / 25.4, 2),
            "rolling_radius_mm": round(rolling_radius_mm, 1),
            "rolling_radius_inches": round(rolling_radius_mm / 25.4, 2),
            "rolling_circumference_mm": round(rolling_circumference_mm, 1),
            "rolling_circumference_meters": round(rolling_circumference_mm / 1000, 3),
            "revolutions_per_km": round(1000000 / rolling_circumference_mm, 1)
        }
        
        # Format the response
        response = f"""Rolling Radius Calculation for {tire_size}:

📏 Tire Specifications:
   • Width: {results['width_mm']} mm
   • Aspect Ratio: {results['aspect_ratio']}%
   • Wheel Diameter: {results['wheel_diameter_inches']}" inches
   • Sidewall Height: {results['sidewall_height_mm']} mm

🔧 Radius Calculations:
   • Static Radius: {results['static_radius_mm']} mm ({results['static_radius_inches']}")
   • Loaded Radius: {results['loaded_radius_mm']} mm ({results['loaded_radius_inches']}")
   • Rolling Radius: {results['rolling_radius_mm']} mm ({results['rolling_radius_inches']}")

🚛 Practical Data:
   • Rolling Circumference: {results['rolling_circumference_meters']} m
   • Revolutions per Kilometer: {results['revolutions_per_km']}
   • Overall Diameter: {round(results['rolling_radius_mm'] * 2 / 25.4, 1)}" inches

💡 Applications:
   • Speedometer calibration
   • Odometer accuracy
   • Gear ratio calculations
   • Load planning and clearance checks"""
        
        return response
        
    except ValueError as e:
        return f"Error parsing tire size '{tire_size}': {str(e)}. Please use format like '295/80R22.5' or '11R22.5'"
    except Exception as e:
        return f"Error calculating rolling radius: {str(e)}"

@tool
def calculate_truck_load_distribution(total_weight_kg: int, axle_configuration: str) -> str:
    """
    Calculate load distribution for different truck axle configurations.
    
    Args:
        total_weight_kg: Total loaded weight of truck in kg
        axle_configuration: Type like "4x2", "6x2", "6x4", "8x4"
        
    Returns:
        Load distribution details and compliance information
    """
    try:
        # Axle weight limits (typical values for India/Europe)
        axle_limits = {
            "single_steer": 7500,    # kg
            "single_drive": 11500,   # kg
            "tandem_drive": 19000,   # kg
            "tridem_drive": 24000,   # kg
            "trailer_single": 10000, # kg
            "trailer_tandem": 18000  # kg
        }
        
        # Parse axle configuration
        config_map = {
            "4x2": {"steer": 1, "drive": 1, "description": "Single steer, single drive"},
            "6x2": {"steer": 1, "drive": 1, "tag": 1, "description": "Single steer, single drive, tag axle"},
            "6x4": {"steer": 1, "drive": 2, "description": "Single steer, tandem drive"},
            "8x4": {"steer": 2, "drive": 2, "description": "Tandem steer, tandem drive"},
            "6x2/4": {"steer": 1, "drive": 1, "lift": 1, "description": "Single steer, single drive, liftable axle"}
        }
        
        if axle_configuration not in config_map:
            return f"Error: Unsupported axle configuration '{axle_configuration}'. Supported: {list(config_map.keys())}"
        
        config = config_map[axle_configuration]
        
        # Basic weight distribution percentages
        if axle_configuration == "4x2":
            steer_weight = total_weight_kg * 0.30  # 30% on steer
            drive_weight = total_weight_kg * 0.70  # 70% on drive
            axle_weights = {
                "steer_axle": round(steer_weight),
                "drive_axle": round(drive_weight)
            }
        elif axle_configuration == "6x4":
            steer_weight = total_weight_kg * 0.25  # 25% on steer
            drive_weight = total_weight_kg * 0.75  # 75% on tandem drive
            axle_weights = {
                "steer_axle": round(steer_weight),
                "drive_tandem": round(drive_weight)
            }
        elif axle_configuration == "6x2":
            steer_weight = total_weight_kg * 0.30  # 30% on steer
            drive_weight = total_weight_kg * 0.55  # 55% on drive
            tag_weight = total_weight_kg * 0.15   # 15% on tag
            axle_weights = {
                "steer_axle": round(steer_weight),
                "drive_axle": round(drive_weight),
                "tag_axle": round(tag_weight)
            }
        else:
            # Generic calculation
            num_axles = sum(config.values()) if isinstance(config, dict) else 3
            avg_weight = total_weight_kg / num_axles
            axle_weights = {"average_per_axle": round(avg_weight)}
        
        # Check compliance
        violations = []
        max_legal_weight = 0
        
        for axle_name, weight in axle_weights.items():
            if "steer" in axle_name:
                limit = axle_limits["single_steer"]
                max_legal_weight += limit
                if weight > limit:
                    violations.append(f"{axle_name}: {weight}kg exceeds {limit}kg limit")
            elif "drive_tandem" in axle_name:
                limit = axle_limits["tandem_drive"]
                max_legal_weight += limit
                if weight > limit:
                    violations.append(f"{axle_name}: {weight}kg exceeds {limit}kg limit")
            elif "drive_axle" in axle_name:
                limit = axle_limits["single_drive"]
                max_legal_weight += limit
                if weight > limit:
                    violations.append(f"{axle_name}: {weight}kg exceeds {limit}kg limit")
            elif "tag" in axle_name:
                limit = axle_limits["trailer_single"]
                max_legal_weight += limit
                if weight > limit:
                    violations.append(f"{axle_name}: {weight}kg exceeds {limit}kg limit")
        
        # Generate response
        response = f"""🚛 Load Distribution Analysis for {axle_configuration} Configuration:

📋 Configuration Details:
   • Type: {config['description']}
   • Total Weight: {total_weight_kg:,} kg
   • Maximum Legal Weight: {max_legal_weight:,} kg

⚖️ Axle Weight Distribution:"""
        
        for axle_name, weight in axle_weights.items():
            response += f"\n   • {axle_name.replace('_', ' ').title()}: {weight:,} kg"
        
        if violations:
            response += f"\n\n⚠️ Weight Violations:\n"
            for violation in violations:
                response += f"   • {violation}\n"
            response += "\n🔧 Recommendations:\n"
            response += "   • Redistribute load or reduce cargo weight\n"
            response += "   • Consider different axle configuration\n"
            response += "   • Check local regulations for specific limits"
        else:
            response += f"\n\n✅ Compliance Status: All axle weights within legal limits"
            remaining_capacity = max_legal_weight - total_weight_kg
            if remaining_capacity > 0:
                response += f"\n📈 Additional Capacity: {remaining_capacity:,} kg available"
        
        response += f"\n\n💡 Notes:\n"
        response += f"   • Values based on typical regulations (India/Europe)\n"
        response += f"   • Actual limits may vary by region\n"
        response += f"   • Consider dynamic load shifting during transport"
        
        return response
        
    except Exception as e:
        return f"Error calculating load distribution: {str(e)}"

@tool
def estimate_fuel_consumption(distance_km: int, load_weight_kg: int, truck_type: str = "heavy") -> str:
    """
    Estimate fuel consumption for truck trips based on distance, load, and truck type.
    
    Args:
        distance_km: Trip distance in kilometers
        load_weight_kg: Total loaded weight in kg
        truck_type: Type of truck ("light", "medium", "heavy", "trailer")
        
    Returns:
        Fuel consumption estimates and cost calculations
    """
    try:
        # Base fuel consumption rates (liters per 100km)
        base_consumption = {
            "light": 12,    # Light commercial vehicles (up to 7.5t)
            "medium": 18,   # Medium trucks (7.5-16t)
            "heavy": 28,    # Heavy trucks (16-40t)
            "trailer": 35   # Truck-trailer combinations (40t+)
        }
        
        if truck_type not in base_consumption:
            return f"Error: Unsupported truck type '{truck_type}'. Use: {list(base_consumption.keys())}"
        
        base_rate = base_consumption[truck_type]
        
        # Load factor adjustments (fuel consumption increases with weight)
        if truck_type == "light":
            max_weight = 7500
        elif truck_type == "medium":
            max_weight = 16000
        elif truck_type == "heavy":
            max_weight = 25000
        else:  # trailer
            max_weight = 40000
        
        # Calculate load factor (0-1, where 1 is max capacity)
        load_factor = min(load_weight_kg / max_weight, 1.2)  # Allow 20% overload
        
        # Adjust consumption based on load (empty truck uses ~70% of full-load consumption)
        consumption_multiplier = 0.70 + (0.30 * load_factor)
        adjusted_consumption_per_100km = base_rate * consumption_multiplier
        
        # Calculate total consumption
        total_consumption_liters = (distance_km / 100) * adjusted_consumption_per_100km
        
        # Estimate costs (approximate diesel prices)
        diesel_price_per_liter = 90  # INR per liter (adjust as needed)
        total_fuel_cost = total_consumption_liters * diesel_price_per_liter
        
        # Additional calculations
        co2_emissions_kg = total_consumption_liters * 2.68  # kg CO2 per liter diesel
        
        response = f"""⛽ Fuel Consumption Estimate:

🚛 Trip Details:
   • Distance: {distance_km:,} km
   • Load Weight: {load_weight_kg:,} kg
   • Truck Type: {truck_type.title()}
   • Load Factor: {round(load_factor * 100, 1)}%

📊 Consumption Analysis:
   • Base Consumption: {base_rate} L/100km
   • Adjusted Consumption: {round(adjusted_consumption_per_100km, 1)} L/100km
   • Total Fuel Required: {round(total_consumption_liters, 1)} liters

💰 Cost Estimates:
   • Fuel Cost: ₹{round(total_fuel_cost):,}
   • Cost per km: ₹{round(total_fuel_cost/distance_km, 2)}
   • Cost per tonne-km: ₹{round(total_fuel_cost/(distance_km * load_weight_kg/1000), 2)}

🌍 Environmental Impact:
   • CO₂ Emissions: {round(co2_emissions_kg):,} kg
   • Emissions per km: {round(co2_emissions_kg/distance_km, 2)} kg/km

💡 Optimization Tips:
   • Maintain optimal speed (80-90 km/h)
   • Regular vehicle maintenance
   • Efficient route planning
   • Driver training for fuel-efficient driving
   • Consider load consolidation"""
        
        # Add warnings for overload
        if load_factor > 1.0:
            overload_pct = (load_factor - 1.0) * 100
            response += f"\n\n⚠️ Warning: Vehicle appears overloaded by {round(overload_pct, 1)}%"
            response += f"\n   • Increased fuel consumption and wear"
            response += f"\n   • Potential legal and safety issues"
        
        return response
        
    except Exception as e:
        return f"Error calculating fuel consumption: {str(e)}"